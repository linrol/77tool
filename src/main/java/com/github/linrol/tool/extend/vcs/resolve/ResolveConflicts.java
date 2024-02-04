package com.github.linrol.tool.extend.vcs.resolve;

import com.intellij.diff.DiffRequestFactory;
import com.intellij.diff.InvalidDiffRequestException;
import com.intellij.diff.comparison.ComparisonManager;
import com.intellij.diff.contents.DocumentContent;
import com.intellij.diff.fragments.MergeLineFragment;
import com.intellij.diff.merge.MergeModelBase;
import com.intellij.diff.merge.MergeResult;
import com.intellij.diff.merge.MergeUtil;
import com.intellij.diff.merge.TextMergeChange;
import com.intellij.diff.merge.TextMergeChange.State;
import com.intellij.diff.merge.TextMergeRequest;
import com.intellij.diff.tools.util.base.IgnorePolicy;
import com.intellij.diff.tools.util.text.LineOffsets;
import com.intellij.diff.tools.util.text.LineOffsetsUtil;
import com.intellij.diff.util.DiffUtil;
import com.intellij.diff.util.LineRange;
import com.intellij.diff.util.ThreeSide;
import com.intellij.openapi.application.ReadAction;
import com.intellij.openapi.command.WriteCommandAction;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.progress.ProgressManager;
import com.intellij.openapi.progress.util.BackgroundTaskUtil;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.io.FileTooBigException;
import com.intellij.openapi.vcs.VcsBundle;
import com.intellij.openapi.vcs.VcsException;
import com.intellij.openapi.vcs.merge.MergeData;
import com.intellij.openapi.vcs.merge.MergeProvider;
import com.intellij.openapi.vcs.merge.MergeUtils;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.util.Consumer;
import com.intellij.util.concurrency.annotations.RequiresWriteLock;
import com.intellij.util.containers.ContainerUtil;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import kotlin.collections.CollectionsKt;
import com.github.linrol.tool.utils.FileUtils;
import com.github.linrol.tool.utils.diff.MergeConflictType;
import com.github.linrol.tool.utils.diff.MergeRangeUtil;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

public abstract class ResolveConflicts {

  private static final Logger LOG = Logger.getInstance(ResolveConflicts.class);

  private Project project;

  private VirtualFile file;

  private TextMergeRequest request;
  private MergeModelBase myModel;

  private List<MergeLineFragment> lineFragments;
  private List<MergeConflictType> conflictTypes;

  public static ResolveConflicts getInstance(Project project, MergeProvider provider,
      VirtualFile file) {
    ResolveConflicts conflicts;
    String name = file.getName();
    if (name.equals("pom.xml")) {
      conflicts = new PomResolveConflicts();
    } else if (isSqlFile(name)) {
      conflicts = new SqlResolveConflicts();
    } else {
      return null;
    }
    conflicts.init(project, provider, file);
    if (!conflicts.isReady()) {
      return null;
    }
    return conflicts;
  }

  private static Boolean isSqlFile(String fileName) {
    String pattern = "^(before|after|recovery)_(identity|reconcile|tenantallin)_data.sql$";

    Pattern r = Pattern.compile(pattern);
    Matcher m = r.matcher(fileName);
    return m.matches();
  }

  private Boolean isReady() {
    return request != null && myModel != null && !lineFragments.isEmpty();
  }

  public void init(Project project, MergeProvider provider, VirtualFile file) {
    this.project = project;
    this.file = file;
    ProgressManager.getInstance()
        .runProcessWithProgressSynchronously(() -> {
              initRequest(provider);
            }, VcsBundle.message("multiple.file.merge.dialog.progress.title.resolving.conflicts"), true,
            project);
    initMergeModel();
  }

  private void initRequest(@NotNull MergeProvider provider) {
    DiffRequestFactory requestFactory = DiffRequestFactory.getInstance();

    try {
      MergeData mergeData = provider.loadRevisions(file);
      List<byte[]> byteContents = CollectionsKt.listOf(mergeData.CURRENT, mergeData.ORIGINAL,
          mergeData.LAST);
      List<String> contentTitles = new ArrayList<>();
      contentTitles.add("left");
      contentTitles.add("center");
      contentTitles.add("right");
      String title = "merge";

      Consumer<? super MergeResult> callback = result -> {

        Document document = request.getContents().get(ThreeSide.BASE.getIndex()).getDocument();
        FileUtils.INSTANCE.saveDocument(file, document);
        MergeUtil.reportProjectFileChangeIfNeeded(project, file);

        if (result != MergeResult.CANCEL) {
          List<VirtualFile> markFiles = new ArrayList<>();
          markFiles.add(file);
        }
      };

      request = (TextMergeRequest) requestFactory.createMergeRequest(project, file, byteContents,
          title,
          contentTitles, callback);

      MergeUtils.putRevisionInfos(request, mergeData);
    } catch (InvalidDiffRequestException e) {
      if (e.getCause() instanceof FileTooBigException) {
      } else {
        LOG.error(e);
      }
    } catch (VcsException e) {

    }
  }

  private void initMergeModel() {
    BackgroundTaskUtil.executeAndTryWait(indicator -> () -> {
      try {
        Document document = request.getContents().get(ThreeSide.BASE.getIndex()).getDocument();
        document.setReadOnly(false);
        myModel = new MyMergeModel(project, document);

        indicator.checkCanceled();
        IgnorePolicy ignorePolicy = IgnorePolicy.DEFAULT;

        List<DocumentContent> contents = request.getContents();
        List<CharSequence> sequences = ReadAction.compute(() -> {
          indicator.checkCanceled();
          return ContainerUtil.map(contents,
              content -> content.getDocument().getImmutableCharSequence());
        });
        List<LineOffsets> lineOffsets = ContainerUtil.map(sequences, LineOffsetsUtil::create);

        ComparisonManager manager = ComparisonManager.getInstance();
        lineFragments = manager.mergeLines(sequences.get(0), sequences.get(1), sequences.get(2),
            ignorePolicy.getComparisonPolicy(), indicator);

        conflictTypes = ContainerUtil.map(lineFragments, fragment ->
            MergeRangeUtil.getLineMergeType(fragment, sequences, lineOffsets,
                ignorePolicy.getComparisonPolicy()));
        myModel.setChanges(
            ContainerUtil.map(lineFragments, f -> new LineRange(f.getStartLine(ThreeSide.BASE),
                f.getEndLine(ThreeSide.BASE))));
      } catch (ProcessCanceledException e) {
        throw e;
      } catch (Throwable e) {
        throw e;
      }
    }, null, 60 * 1000, false);

  }

  @RequiresWriteLock
  public Boolean resolveChangeAuto() {
    Map<Integer, List<String>> newContentMap = new HashMap<>();
    for (int i = 0; i < lineFragments.size(); i++) {
      MergeLineFragment fragment = lineFragments.get(i);
      MergeConflictType conflictType = conflictTypes.get(i);

      List<String> newContent = getNewContent(fragment, conflictType);
      if (newContent == null) {
        return false;
      } else {
        newContentMap.put(i, newContent);
      }
    }

    if (newContentMap.size() != conflictTypes.size()) {
      return false;
    }

//    if(myModel.isInsideCommand()){
//    myModel.isInsideCommand();
      WriteCommandAction.runWriteCommandAction(project, () -> {
        //do something
        newContentMap.forEach((index, newContent) -> myModel.replaceChange(index, newContent));
        request.applyResult(MergeResult.RESOLVED);
      });
//    }else {
//      myModel.executeMergeCommand(DiffBundle.message("merge.dialog.apply.non.conflicted.changes.command"), null, UndoConfirmationPolicy.DEFAULT, true, null, () -> {
//        newContentMap.forEach((index, newContent) -> myModel.replaceChange(index, newContent));
//        request.applyResult(MergeResult.RESOLVED);
//      });
//    }
    return true;
  }

  private List<String> getNewContent(MergeLineFragment fragment, MergeConflictType conflictType) {
    if (conflictType.isChange(ThreeSide.LEFT) && conflictType.isChange(ThreeSide.RIGHT)) {
      //冲突
      return getNewContentOfConflict(fragment);
    }

    ThreeSide sourceSide = conflictType.isChange(ThreeSide.LEFT) ? ThreeSide.LEFT : ThreeSide.RIGHT;
    int sourceStartLine = fragment.getStartLine(sourceSide);
    int sourceEndLine = fragment.getEndLine(sourceSide);
    Document sourceDocument = request.getContents().get(sourceSide.getIndex()).getDocument();

    return DiffUtil.getLines(sourceDocument, sourceStartLine, sourceEndLine);
  }

  public Project getProject() {
    return project;
  }

  public VirtualFile getFile() {
    return file;
  }

  public TextMergeRequest getRequest() {
    return request;
  }

  public MergeModelBase getMyModel() {
    return myModel;
  }

  public List<MergeLineFragment> getLineFragments() {
    return lineFragments;
  }

  public List<MergeConflictType> getConflictTypes() {
    return conflictTypes;
  }

  abstract List<String> getNewContentOfConflict(MergeLineFragment fragment);


  private class MyMergeModel extends MergeModelBase<State> {

    MyMergeModel(@Nullable Project project, @NotNull Document document) {
      super(project, document);
    }

    @Override
    protected void reinstallHighlighters(int index) {
    }

    public boolean isInsideCommand() {
      return true;
    }
    @NotNull
    @Override
    protected TextMergeChange.State storeChangeState(int index) {
      return new TextMergeChange.State(
          index,
          getLineStart(index),
          getLineStart(index),

          true,
          true,

          false);
    }
  }
}
