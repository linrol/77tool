package org.intellij.tool.utils;

import com.intellij.concurrency.JobScheduler;
import com.intellij.openapi.progress.ProgressIndicator;
import com.intellij.openapi.progress.ProgressManager;
import com.intellij.openapi.progress.Task;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.roots.ProjectRootManager;
import com.intellij.openapi.ui.Messages;
import com.intellij.openapi.util.Ref;
import com.intellij.openapi.util.ThrowableComputable;
import com.intellij.openapi.vcs.changes.Change;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.util.ThrowableConvertor;
import com.intellij.util.containers.Convertor;
import git4idea.branch.GitBrancher;
import org.intellij.tool.model.RepositoryChange;
import git4idea.GitUtil;
import git4idea.commands.Git;
import git4idea.commands.GitCommand;
import git4idea.commands.GitCommandResult;
import git4idea.commands.GitLineHandler;
import git4idea.config.GitExecutableManager;
import git4idea.config.GitVersion;
import git4idea.fetch.GitFetchResult;
import git4idea.fetch.GitFetchSupport;
import git4idea.repo.GitRepository;
import git4idea.repo.GitRepositoryManager;

import java.util.*;
import java.util.stream.Collectors;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.io.IOException;
import java.net.URI;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;


/**
 * GitLab specific untils
 *
 * @author ppolivka
 * @since 28.10.2015
 */
@SuppressWarnings("Duplicates")
public class GitLabUtil {

    @Nullable
    public static GitRepository getGitRepository(@NotNull Project project, @NotNull VirtualFile file) {
        GitRepositoryManager manager = GitUtil.getRepositoryManager(project);
        List<GitRepository> repositories = manager.getRepositories();
        if (repositories.size() == 0) {
            return null;
        }
        if (repositories.size() == 1) {
            return repositories.get(0);
        }
        GitRepository repository = manager.getRepositoryForFile(file);
        if (repository != null) {
            return repository;
        }
        VirtualFile projectFile = ProjectRootManager.getInstance(project).getFileIndex().getContentRootForFile(file);;
        if (projectFile == null) {
            return null;
        }
        return manager.getRepositoryForFile(projectFile);
    }

    public static List<RepositoryChange> groupByRepository(Project project, List<Change> files) {
        GitRepositoryManager manager = GitUtil.getRepositoryManager(project);
        Map<GitRepository, List<Change>> repoFilesMap = new HashMap<>();
        files.forEach(change -> {
            VirtualFile virtualFile = change.getVirtualFile();
            if (virtualFile == null) {
                return;
            }
            GitRepository repository = manager.getRepositoryForFile(virtualFile);
            repoFilesMap.compute(repository, (k, v) -> {
                if (v == null) {
                    List<Change> list = new ArrayList<>();
                    list.add(change);
                    return list;
                }
                v.add(change);
                return v;
            });
        });

        return repoFilesMap.entrySet().stream().map(entry -> {
            return RepositoryChange.of(entry.getKey(), entry.getValue());
        }).collect(Collectors.toList());
    }

    public static List<GitRepository> getRepositories(Project project) {
        GitRepositoryManager manager = GitUtil.getRepositoryManager(project);
        return manager.getRepositories();
    }

    public static List<GitRepository> getCommonRepositories(Project project, String... branch) {
        return getRepositories(project).stream().filter(f -> {
            List<String> remoteBranch = f.getBranches().getRemoteBranches().stream().map(b -> {
                return b.getNameForRemoteOperations();
            }).collect(Collectors.toList());
            return new HashSet<>(remoteBranch).containsAll(Arrays.asList(branch));
        }).collect(Collectors.toList());
    }

    public static List<GitRepository> getRepositories(Project project, List<Change> files) {
        GitRepositoryManager manager = GitUtil.getRepositoryManager(project);
        return files.stream().filter(f -> {
            return f.getVirtualFile() != null;
        }).map(m -> manager.getRepositoryForFile(m.getVirtualFile())).distinct().collect(Collectors.toList());
    }

    public static boolean isGitLabUrl(String testUrl, String url) {
        try {
            URI fromSettings = new URI(testUrl);
            String fromSettingsHost = fromSettings.getHost();

            String patternString = "(\\w+://)(.+@)*([\\w\\d\\.\\-]+)(:[\\d]+){0,1}/*(.*)|(.+@)*([\\w\\d\\.\\-]+):(.*)";
            Pattern pattern = Pattern.compile(patternString);
            Matcher matcher = pattern.matcher(url);
            String fromUrlHost = "";
            if (matcher.matches()) {
                String group3 = matcher.group(3);
                String group7 = matcher.group(7);
                if (StringUtils.isBlank(group3)) {
                    fromUrlHost = group3;
                } else if (!StringUtils.isBlank(group7)) {
                    fromUrlHost = group7;
                }
            }
            return fromSettingsHost != null && removeNotAlpha(fromSettingsHost).equals(removeNotAlpha(fromUrlHost));
        } catch (Exception e) {
            return false;
        }
    }

    public static String removeNotAlpha(String input) {
        input = input.replaceAll("[^a-zA-Z0-9]", "");
        input = input.toLowerCase();
        return input;
    }

    public static boolean addGitLabRemote(@NotNull Project project,
                                          @NotNull GitRepository repository,
                                          @NotNull String remote,
                                          @NotNull String url) {
        GitLineHandler handler = new GitLineHandler(project, repository.getRoot(), GitCommand.REMOTE);
        handler.setSilent(true);
        handler.addParameters("add", remote, url);
        GitCommandResult result = Git.getInstance().runCommand(handler);
        if (result.getExitCode() != 0) {
            // showErrorDialog(project, "New remote origin cannot be added to this project.", "Cannot Add New Remote");
            return false;
        }
        // catch newly added remote
        repository.update();
        return true;
    }

    /**
     * use getSavedPathToGit() to get the path from settings if there's any or use GitExecutableManager.getPathToGit()/GitExecutableManager.getPathToGit(Project) to get git executable with auto-detection
     *
     * @param project
     * @return
     */
    public static boolean testGitExecutable(final Project project) {
        GitExecutableManager manager = GitExecutableManager.getInstance();
        final String executable = manager.getPathToGit(project);
        final GitVersion version;
        try {
            version = manager.getVersion(project);
        } catch (Exception e) {
            // showErrorDialog(project, "Cannot find git executable.", "Cannot Find Git");
            return false;
        }

        if (!version.isSupported()) {
            // showErrorDialog(project, "Your version of git is not supported.", "Cannot Find Git");
            return false;
        }
        return true;
    }

    public static <T> T computeValueInModal(@NotNull Project project,
                                            @NotNull String caption,
                                            @NotNull final ThrowableConvertor<ProgressIndicator, T, IOException> task) throws IOException {
        final Ref<T> dataRef = new Ref<T>();
        final Ref<Throwable> exceptionRef = new Ref<Throwable>();
        ProgressManager.getInstance().run(new Task.Modal(project, caption, true) {
            public void run(@NotNull ProgressIndicator indicator) {
                try {
                    dataRef.set(task.convert(indicator));
                } catch (Throwable e) {
                    exceptionRef.set(e);
                }
            }
        });
        if (!exceptionRef.isNull()) {
            Throwable e = exceptionRef.get();
            if (e instanceof IOException) {
                throw ((IOException) e);
            }
            if (e instanceof RuntimeException) {
                throw ((RuntimeException) e);
            }
            if (e instanceof Error) {
                throw ((Error) e);
            }
            throw new RuntimeException(e);
        }
        return dataRef.get();
    }

    public static <T> T computeValueInModal(@NotNull Project project,
                                            @NotNull String caption,
                                            @NotNull final Convertor<ProgressIndicator, T> task) {
        return computeValueInModal(project, caption, true, task);
    }

    public static <T> T computeValueInModal(@NotNull Project project,
                                            @NotNull String caption,
                                            boolean canBeCancelled,
                                            @NotNull final Convertor<ProgressIndicator, T> task) {
        final Ref<T> dataRef = new Ref<T>();
        final Ref<Throwable> exceptionRef = new Ref<Throwable>();
        ProgressManager.getInstance().run(new Task.Modal(project, caption, canBeCancelled) {
            public void run(@NotNull ProgressIndicator indicator) {
                try {
                    dataRef.set(task.convert(indicator));
                } catch (Throwable e) {
                    exceptionRef.set(e);
                }
            }
        });
        if (!exceptionRef.isNull()) {
            Throwable e = exceptionRef.get();
            if (e instanceof RuntimeException) {
                throw ((RuntimeException) e);
            }
            if (e instanceof Error) {
                throw ((Error) e);
            }
            throw new RuntimeException(e);
        }
        return dataRef.get();
    }

    public static <T> T runInterruptable(@NotNull final ProgressIndicator indicator,
                                         @NotNull ThrowableComputable<T, IOException> task) throws IOException {
        ScheduledFuture<?> future = null;
        try {
            final Thread thread = Thread.currentThread();
            future = addCancellationListener(indicator, thread);

            return task.compute();
        } finally {
            if (future != null) {
                future.cancel(true);
            }
            Thread.interrupted();
        }
    }

    @NotNull
    private static ScheduledFuture<?> addCancellationListener(@NotNull final ProgressIndicator indicator,
                                                              @NotNull final Thread thread) {
        return addCancellationListener(new Runnable() {
            @Override
            public void run() {
                if (indicator.isCanceled()) {
                    thread.interrupt();
                }
            }
        });
    }

    @NotNull
    private static ScheduledFuture<?> addCancellationListener(@NotNull Runnable run) {
        return JobScheduler.getScheduler().scheduleWithFixedDelay(run, 1000, 300, TimeUnit.MILLISECONDS);
    }

    @Messages.YesNoResult
    public static boolean showYesNoDialog(@Nullable Project project, @NotNull String title, @NotNull String message) {
        return Messages.YES == Messages.showYesNoDialog(project, message, title, Messages.getQuestionIcon());
    }
    @NotNull
    public static GitFetchResult fetch(@NotNull Project project) {
        return fetch(project, GitUtil.getRepositories(project));
    }

    @NotNull
    public static GitFetchResult fetch(@NotNull Project project, Collection<GitRepository> repositories) {
        return GitFetchSupport.fetchSupport(project).fetchAllRemotes(repositories);
    }
}