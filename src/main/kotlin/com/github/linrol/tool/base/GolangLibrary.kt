package com.github.linrol.tool.base

import jnr.ffi.LibraryLoader
import java.io.File
import java.nio.file.Files

object NativeLibLoader {
    fun loadLibraryFromJar(libName: String): String {
        val libPath = "/lib/$libName" // JAR 中的库文件路径
        val inputStream = NativeLibLoader::class.java.getResourceAsStream(libPath)
            ?: throw IllegalArgumentException("Library $libPath not found in JAR")

        // 创建临时文件
        val tempFile = File.createTempFile(libName, null)
        tempFile.deleteOnExit()

        // 将库文件写入临时文件
        Files.copy(inputStream, tempFile.toPath(), java.nio.file.StandardCopyOption.REPLACE_EXISTING)

        return tempFile.absolutePath
    }
}

interface GolangLibrary {
    fun add(a: Int, b: Int): Int

    fun subtract(a: Int, b: Int): Int

    companion object {
        private val libPath = NativeLibLoader.loadLibraryFromJar("libGolang.dylib")
        private val INSTANCE: GolangLibrary = LibraryLoader.create(GolangLibrary::class.java).load(libPath)  // "add" 对应于生成的 libadd.so 文件名

        fun getInstance(): GolangLibrary {
            return INSTANCE
        }
    }

}