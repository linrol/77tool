package com.github.linrol.tool.lang

import com.github.linrol.tool.model.GitCmd
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.command.WriteCommandAction
import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.project.DumbAwareAction
import java.util.*

class BackendLangAction : DumbAwareAction() {

    companion object {
        private val logger = logger<BackendLangAction>()
    }

    override fun actionPerformed(event: AnActionEvent) {
        event.project ?: return
        val place = event.place // ProjectViewPopup EditorPopup
        if (place == "EditorPopup") {
            // 代码中选中的文本翻译
            editorSelectedProcessor(event)
        }
        if (place == "ProjectViewPopup") {
            // 对csv文件整体翻译没有被翻译的中文
            csvTranslateProcessor()
        }
    }

    private fun editorSelectedProcessor(event: AnActionEvent) {
        val editor: Editor = event.dataContext.getData("editor") as? Editor ?: return
        val document = editor.document
        val selectedText = editor.selectionModel.selectedText ?: return
        // 翻译
        val translater = LangTranslater()
        if (translater.canProxy) {
            GitCmd.log(event.project!!, "使用谷歌翻译")
        } else {
            GitCmd.log(event.project!!, "使用百度翻译")
        }
        val translateText: String = translater.translate(selectedText)
        if (selectedText == translateText) {
            return
        }
        // 准备替换内容
        val resourceKey = translateText.replace(" ", "_").uppercase(Locale.getDefault())
        val replaceText = "StrResUtils.getCurrentAppStr(StrResConstants.${resourceKey})"
        val documentText = document.text
        val newText = documentText.replace("\"${selectedText}\"", replaceText)
        WriteCommandAction.runWriteCommandAction(event.project) {
            document.setText(newText)
        }
    }

    private fun csvTranslateProcessor() {

    }
}