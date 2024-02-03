package com.github.linrol.tool.utils

import com.intellij.openapi.editor.Document
import com.intellij.openapi.vfs.VirtualFile
import java.io.BufferedWriter
import java.io.FileWriter
import java.io.IOException

/**
 * GitLab specific untils
 *
 * @author ppolivka
 * @since 28.10.2015
 */
object FileUtils {
    fun saveDocument(file: VirtualFile, document: Document) {
        saveText(file, document.text)
    }

    private fun saveText(file: VirtualFile, text: String) {
        var writer: BufferedWriter? = null
        try {
            writer = BufferedWriter(FileWriter(file.canonicalPath.toString()))
            writer.write(text)
            writer.flush()
            writer.close()
        } catch (e: IOException) {
            throw RuntimeException(e)
        } finally {
            if (writer != null) {
                try {
                    writer.close()
                } catch (e: IOException) {
                    throw RuntimeException(e)
                }
            }
        }
    }
}