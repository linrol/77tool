package com.github.linrol.tool.constants

import org.gitlab4j.api.GitLabApi

const val GITLAB_URL = "http://gitlab.q7link.com/"
const val ACCESS_TOKEN = "sTyo1zhgMyDEsq9Mxm1H"
const val BUILD_GIT_PATH = "backend/apps/build"

val gitLabApi = GitLabApi(GITLAB_URL, ACCESS_TOKEN)
