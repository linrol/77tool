package com.github.linrol.tool.extend.vcs;

import static com.intellij.openapi.vcs.VcsNotifier.STANDARD_NOTIFICATION;

import com.github.linrol.tool.extend.vcs.resolve.ResolveConflicts;
import com.intellij.notification.NotificationType;
import com.intellij.openapi.progress.ProgressManager;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.vcs.FilePath;
import com.intellij.openapi.vcs.VcsBundle;
import com.intellij.openapi.vcs.VcsException;
import com.intellij.openapi.vcs.VcsNotifier;
import com.intellij.openapi.vcs.impl.AbstractVcsHelperImpl;
import com.intellij.openapi.vcs.merge.MergeDialogCustomizer;
import com.intellij.openapi.vcs.merge.MergeProvider;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.vcsUtil.VcsUtil;
import git4idea.util.GitFileUtils;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.jetbrains.annotations.NotNull;

public class AbstractVcsHelperImplEx extends AbstractVcsHelperImpl {

  private Project project;

  private Runnable callAfterMerged;


  protected AbstractVcsHelperImplEx(@NotNull Project project) {
    super(project);
    this.project = project;
  }
  @Override
  @NotNull
  public List<VirtualFile> showMergeDialog(@NotNull List<? extends VirtualFile> files,
      @NotNull MergeProvider provider,
      @NotNull MergeDialogCustomizer mergeDialogCustomizer) {
    if (files.isEmpty()) return Collections.emptyList();
    try {
      autoResolve(files, provider);
    }catch (Throwable e){
      e.printStackTrace();
      VcsNotifier vcsNotifier = VcsNotifier.getInstance(project);
      vcsNotifier.notify(STANDARD_NOTIFICATION.createNotification(e.toString(), NotificationType.ERROR));
    }
    List<VirtualFile> virtualFiles = super.showMergeDialog(files, provider, mergeDialogCustomizer);
    changeVersionAfterMerged(files, virtualFiles);
    return virtualFiles;
  }

  private void autoResolve(List<? extends VirtualFile> files, MergeProvider provider){
    Map<VirtualFile, List<FilePath>> toAddMap = new HashMap<>();
    for (int i = files.size() - 1; i >= 0; i--) {
      VirtualFile file = files.get(i);
      ResolveConflicts conflicts = ResolveConflicts.getInstance(project, provider, file);
      if(conflicts == null){
        continue;
      }
      Boolean resolveChangeAuto = conflicts.resolveChangeAuto();
      if(resolveChangeAuto){
        VirtualFile root = VcsUtil.getVcsRootFor(project, file);
        List<FilePath> toAdds = toAddMap.getOrDefault(root, new ArrayList<>());
        toAdds.add(VcsUtil.getFilePath(file));
        toAddMap.put(root, toAdds);
        files.remove(i);
      }
    }

    ProgressManager.getInstance()
        .runProcessWithProgressSynchronously(()->{
              toAddMap.forEach((root, toAdd)->{
                try {
                  GitFileUtils.addPathsForce(project, root, toAdd);
                } catch (VcsException e) {
                  throw new RuntimeException(e);
                }
              });
            },
            VcsBundle.message("multiple.file.merge.dialog.progress.title.resolving.conflicts"),
            true, project);

  }

  private void changeVersionAfterMerged(List<? extends VirtualFile> files, List<VirtualFile> virtualFiles) {
    if (!virtualFiles.isEmpty() && virtualFiles.size() == files.size()) {
      if (callAfterMerged != null) {
        callAfterMerged.run();
      }
    }
    clearCallAfterMerged();
  }

  public void setCallAfterMerged(Runnable callAfterMerged) {
    this.callAfterMerged = callAfterMerged;
  }

  public void clearCallAfterMerged() {
    callAfterMerged = null;
  }
}
