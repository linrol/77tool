package com.github.linrol.tool.base

import com.intellij.openapi.actionSystem.UpdateInBackground
import com.intellij.openapi.project.DumbAwareAction

abstract class AbstractDumbAction : DumbAwareAction, UpdateInBackground {
    protected constructor(text: String) : super(text)
    protected constructor() : super()
}