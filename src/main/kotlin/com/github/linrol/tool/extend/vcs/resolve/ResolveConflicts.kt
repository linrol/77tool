package com.github.linrol.tool.extend.vcs.resolve

import com.github.linrol.tool.utils.FileUtils.saveDocument
import com.github.linrol.tool.utils.MergeConflictType
import com.github.linrol.tool.utils.MergeRangeUtil.getLineMergeType
import com.intellij.diff.DiffRequestFactory
import com.intellij.diff.InvalidDiffRequestException
import com.intellij.diff.comparison.ComparisonManager
import com.intellij.diff.contents.DocumentContent
import com.intellij.diff.fragments.MergeLineFragment
import com.intellij.diff.merge.*
import com.intellij.diff.tools.util.base.IgnorePolicy
import com.intellij.diff.tools.util.text.LineOffsetsUtil
import com.intellij.diff.util.DiffUtil
import com.intellij.diff.util.LineRange
import com.intellij.diff.util.ThreeSide
import com.intellij.openapi.application.ReadAction
import com.intellij.openapi.command.WriteCommandAction
import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.editor.Document
import com.intellij.openapi.progress.ProgressIndicator
import com.intellij.openapi.progress.ProgressManager
import com.intellij.openapi.progress.util.BackgroundTaskUtil
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.io.FileTooBigException
import com.intellij.openapi.vcs.VcsBundle
import com.intellij.openapi.vcs.VcsException
import com.intellij.openapi.vcs.merge.MergeProvider
import com.intellij.openapi.vcs.merge.MergeUtils.putRevisionInfos
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.util.Consumer
import com.intellij.util.concurrency.annotations.RequiresWriteLock
import com.intellij.util.containers.ContainerUtil
import java.util.regex.Pattern

abstract class ResolveConflicts {
    lateinit var project: Project

    lateinit var request: TextMergeRequest

    private lateinit var file: VirtualFile

    private lateinit var myModel: MergeModelBase<*>

    private lateinit var lineFragments: List<MergeLineFragment>

    private lateinit var conflictTypes: List<MergeConflictType>

    private val isReady: Boolean get() = lineFragments.isNotEmpty()

    fun init(project: Project, provider: MergeProvider, file: VirtualFile) {
        this.project = project
        this.file = file
        ProgressManager.getInstance().runProcessWithProgressSynchronously(
            {
                initRequest(provider)
            }, VcsBundle.message("multiple.file.merge.dialog.progress.title.resolving.conflicts"), true, project
        )
        initMergeModel()
    }

    private fun initRequest(provider: MergeProvider) {
        val requestFactory = DiffRequestFactory.getInstance()

        try {
            val mergeData = provider.loadRevisions(file)
            val byteContents = listOf(mergeData.CURRENT, mergeData.ORIGINAL, mergeData.LAST)
            val contentTitles: MutableList<String> = ArrayList()
            contentTitles.add("left")
            contentTitles.add("center")
            contentTitles.add("right")
            val title = "merge"

            val callback: Consumer<in MergeResult> = Consumer { result: MergeResult ->
                val document = request.contents[ThreeSide.BASE.index].document
                saveDocument(file, document)
                MergeUtil.reportProjectFileChangeIfNeeded(project, file)
                if (result != MergeResult.CANCEL) {
                    val markFiles: MutableList<VirtualFile?> = ArrayList()
                    markFiles.add(file)
                }
            }

            request = requestFactory.createMergeRequest(project, file, byteContents, title, contentTitles, callback) as TextMergeRequest

            putRevisionInfos(request, mergeData)
        } catch (e: InvalidDiffRequestException) {
            if (e.cause !is FileTooBigException) {
                logger.error(e)
            }
        } catch (e: VcsException) {
            logger.error(e)
        }
    }

    private fun initMergeModel() {
        BackgroundTaskUtil.executeAndTryWait({ indicator: ProgressIndicator ->
            Runnable {
                try {
                    val document = request.contents[ThreeSide.BASE.index].document
                    document.setReadOnly(false)
                    myModel = MyMergeModel(project, document)

                    indicator.checkCanceled()
                    val ignorePolicy = IgnorePolicy.DEFAULT

                    val contents = request.contents
                    val sequences = ReadAction.compute<List<CharSequence>, RuntimeException> {
                        indicator.checkCanceled()
                        ContainerUtil.map(contents) { content: DocumentContent -> content.document.immutableCharSequence }
                    }
                    val lineOffsets = ContainerUtil.map(sequences) { text: CharSequence ->
                        LineOffsetsUtil.create(text)
                    }

                    val manager = ComparisonManager.getInstance()
                    lineFragments = manager.mergeLines(sequences[0], sequences[1], sequences[2], ignorePolicy.comparisonPolicy, indicator)

                    conflictTypes = ContainerUtil.map(lineFragments) { fragment: MergeLineFragment ->
                        getLineMergeType(fragment, sequences, lineOffsets, ignorePolicy.comparisonPolicy)
                    }
                    myModel.setChanges(ContainerUtil.map(lineFragments) { f: MergeLineFragment ->
                        LineRange(f.getStartLine(ThreeSide.BASE), f.getEndLine(ThreeSide.BASE))
                    })
                } catch (e: Throwable) {
                    throw e
                }
            }
        }, null, (60 * 1000).toLong(), false)
    }

    @RequiresWriteLock
    fun resolveChangeAuto(): Boolean {
        val newContentMap: MutableMap<Int, List<String>> = HashMap()
        for (i in lineFragments.indices) {
            val fragment = lineFragments[i]
            val conflictType = conflictTypes[i]

            val newContent = getNewContent(fragment, conflictType) ?: return false
            newContentMap[i] = newContent
        }
        if (newContentMap.size != conflictTypes.size) {
            return false
        }
        WriteCommandAction.runWriteCommandAction(project) {
            //do something
            newContentMap.forEach { (index: Int, newContent: List<String>) -> myModel.replaceChange(index, newContent) }
            request.applyResult(MergeResult.RESOLVED)
        }
        return true
    }

    private fun getNewContent(fragment: MergeLineFragment, conflictType: MergeConflictType): MutableList<String>? {
        if (conflictType.isChange(ThreeSide.LEFT) && conflictType.isChange(ThreeSide.RIGHT)) {
            //冲突
            return getNewContentOfConflict(fragment)
        }

        val sourceSide = if (conflictType.isChange(ThreeSide.LEFT)) ThreeSide.LEFT else ThreeSide.RIGHT
        val sourceStartLine = fragment.getStartLine(sourceSide)
        val sourceEndLine = fragment.getEndLine(sourceSide)
        val sourceDocument = request.contents[sourceSide.index].document

        return DiffUtil.getLines(sourceDocument, sourceStartLine, sourceEndLine)
    }

    abstract fun getNewContentOfConflict(fragment: MergeLineFragment): MutableList<String>?


    private inner class MyMergeModel(project: Project, document: Document) : MergeModelBase<TextMergeChange.State>(project, document) {
        override fun reinstallHighlighters(index: Int) {
        }

        override fun isInsideCommand(): Boolean {
            return true
        }

        override fun storeChangeState(index: Int): TextMergeChange.State {
            return TextMergeChange.State(
                index,
                getLineStart(index),
                getLineStart(index),
                true,
                true,
                false
            )
        }
    }

    companion object {
        private val logger = logger<ResolveConflicts>()

        fun getInstance(project: Project, provider: MergeProvider, file: VirtualFile): ResolveConflicts? {
            val conflicts: ResolveConflicts
            val name = file.name
            conflicts = if (name == "pom.xml") {
                PomResolveConflicts()
            } else if (isSqlFile(name)) {
                SqlResolveConflicts()
            } else {
                return null
            }
            conflicts.init(project, provider, file)
            if (!conflicts.isReady) {
                return null
            }
            return conflicts
        }

        private fun isSqlFile(fileName: String): Boolean {
            val pattern = "^(before|after|recovery)_(identity|reconcile|tenantallin)_data.sql$"
            val r = Pattern.compile(pattern)
            val m = r.matcher(fileName)
            return m.matches()
        }
    }
}
