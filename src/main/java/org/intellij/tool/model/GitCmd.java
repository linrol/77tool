package org.intellij.tool.model;

import com.intellij.dvcs.repo.Repository;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.progress.ProgressIndicator;
import com.intellij.openapi.progress.ProgressManager;
import com.intellij.openapi.progress.Task;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.Messages;
import com.intellij.openapi.vcs.VcsException;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.openapi.wm.ToolWindow;
import com.intellij.openapi.wm.ToolWindowManager;
import git4idea.commands.*;
import org.intellij.tool.toolwindow.ToolWindowConsole;
import org.intellij.tool.utils.StringUtils;

import git4idea.repo.GitRepository;
import org.apache.commons.lang3.exception.ExceptionUtils;
import org.jetbrains.annotations.NotNull;

import java.awt.EventQueue;
import java.util.Arrays;
import java.util.List;

public class GitCmd {

    private static final Logger logger = Logger.getInstance(GitCmd.class);

    Project project;

    GitRepository repository;

    VirtualFile root;

    GitLineHandler handler;

    GitCommand command;

    public GitCmd(Project project, GitRepository repository) {
        this.repository = repository;
        this.project = project;
        this.root = repository.getRoot();
    }

    public Project getProject() {
        return project;
    }

    public void setProject(Project project) {
        this.project = project;
    }

    public Repository getRepository() {
        return repository;
    }

    public void setRepository(GitRepository repository) {
        this.repository = repository;
    }

    public GitLineHandler getHandler() {
        return handler;
    }

    public void setHandler(GitLineHandler handler) {
        this.handler = handler;
    }

    public VirtualFile getRoot() {
        return root;
    }

    public void setRoot(VirtualFile root) {
        this.root = root;
    }

    public GitCmd addParameters(String... parameters) {
        Arrays.asList(parameters).forEach(handler::addParameters);
        return this;
    }

    public GitCmd build(GitCommand command, String... parameters) {
        this.command = command;
        return build(command, Arrays.asList(parameters));
    }

    public GitCmd build(GitCommand command, List<String> parameters) {
        this.command = command;
        GitLineHandler handler = new GitLineHandler(getProject(), getRoot(), command);
        parameters.forEach(handler::addParameters);
        this.handler = handler;
        return this;
    }

    public GitCmd config(boolean silent, boolean stdoutSuppressed, String... urls) {
        this.handler.setUrls(Arrays.asList(urls));
        this.handler.setSilent(silent);
        this.handler.setStdoutSuppressed(stdoutSuppressed);
        return this;
    }

    public GitCommandResult run() {
        try {
            String runString = this.handler.printableCommandLine();
            logger.debug(runString);
            String title = String.format("Git %s running", this.command);
            GitCommandResult ret = ProgressManager.getInstance().run(new Task.WithResult<GitCommandResult, VcsException>(project, title, true) {
                @Override
                protected GitCommandResult compute(@NotNull ProgressIndicator indicator) {
                    return Git.getInstance().runCommand(handler);
                }
            });
            // GitCommandResult ret = Git.getInstance().runCommand(this.handler);
            if (!ret.success()) {
                String errorString = ret.getErrorOutputAsJoinedString();
                logger.info(String.format("Git run command:%s failed case by:%s", runString, errorString));
                throw new RuntimeException(errorString);
            }
            return ret;
        } catch (VcsException | ProcessCanceledException e) {
            throw new RuntimeException(ExceptionUtils.getRootCauseMessage(e));
        }
    }

    public static void clear() {
        ToolWindowConsole.clear();
    }

    public void log(String msg) {
        log(project, msg);
    }

    public static void log(Project project, String msg) {
        ToolWindow toolWindow = ToolWindowManager.getInstance(project).getToolWindow("77tool");
        if (toolWindow == null) {
            return;
        }
        try {
            ApplicationManager.getApplication().invokeLater(() -> {
                toolWindow.activate(() -> {
                    ToolWindowConsole.show();
                    ToolWindowConsole.log(project, msg);
                });
            });
            // EventQueue.invokeAndWait(() -> );
        } catch (Exception e) {
            e.printStackTrace();
        }
        // toolWindow.show();
    }

    public String showInputDialog() {
        try {
            StringBuffer input = new StringBuffer();
            EventQueue.invokeAndWait(() -> {
                String cm = Messages.showInputDialog(project, "Input commit message:", String.format("%s create branch merge request", project.getName()), Messages.getInformationIcon());
                if (!StringUtils.isBlank(cm)) {
                    if (!"null".equals(cm)) {
                        input.append(cm);
                    }
                }
            });
            return input.toString();
        } catch (Exception e){
            e.printStackTrace();
            return null;
        }
    }

    public String getRemoteUrl() {
        return repository.getRemotes().stream().flatMap(m -> m.getPushUrls().stream()).filter(f -> !StringUtils.isBlank(f)).findAny().orElse(null);
    }

    public String getCurrentBranchName() {
        return repository.getCurrentBranchName();
    }
}
