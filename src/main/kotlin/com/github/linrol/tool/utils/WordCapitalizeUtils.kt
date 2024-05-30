package com.github.linrol.tool.utils

import com.intellij.openapi.diagnostic.logger
import java.util.regex.Pattern

object WordCapitalizeUtils {

    //菜单(包含单据类型），按钮名，动作按钮, 字段名，枚举值名，表单模板预置数据（名称， 字段名），打印模板（名称），要转为每个单词首字母大写，其他保持不变
    private var namespaceList: List<String> = listOf(
        "baseapp_menu.",  //菜单
        "baseapp_bill_type.",  //单据类型
        "baseapp_business_type.",  //业务类型
        "baseapp_action.",  //动作按钮
        "baseapp_chapter.",
        "baseapp_chapter_content.",
        "baseapp_change_report.",
        "str.baseapp.",  //按钮中可能资源
        "front.initdata.Button.",  //按钮
        "front.initdata.ButtonContainer.",  //按钮
        "entity.title",  //对象名
        "field.title.",  //字段名
        "enumValue.title.",  //枚举值名
        "front.initdata.BillTypeTemplate.",  //表单模板
        "front.initdata.FormViewField.",  //字段
        "front.initdata.FormView.",  //字段
        "front.initdata.FormViewContent.",  //字段
        "front.initdata.FormTemplate.",  //字段
        "baseapp_code_rule_value_field.",  //字段
        "baseapp_budget_source_bill_class_item.",  //字段
        "baseapp_list_columns_definition.",  //字段
        "baseapp_report_definition.",  //字段
        "baseapp_report_definition_layout.",  //字段
        "baseapp_report_schema_field.",  //字段
        "baseapp_resource.",  //字段
        "baseapp_portalet.",  //字段
        "baseapp_portalet_enhance.",  //字段
        "baseapp_list_column.",  //字段
        "baseapp_list_column_schema.",  //字段
        "baseapp_report_criteria_schema.",
        "baseapp_migrate_object_type.",
        "baseapp_migrate_object_type_field.",
        "baseapp_object_mc_policy_field_def.",
        "baseapp_query_definition_group.",
        "baseapp_query_item_schema.",
        "front.initdata.FormSchemaField." //字段
    )

    private val logger = logger<WordCapitalizeUtils>()

    fun apply(resKey: String, chinese: String, english: String): String {
        runCatching {
            if (!containsChinese(chinese)) {
                return english // 如果中文中所有的字符都是英文，则不改变大小写（因为可能是公式表达式）
            }
            if (namespaceList.contains(resKey)) {
                return allWordsCapitalize(english) // 特定的namespace的词条，要求每个单词首字母大写（介词除非是第一个，否则首字母不大写）
            }
            return replaceFirstCharCapitalize(english) // 行首字母大写
        }.getOrElse {
            logger.error("word capitalize error:${it.message}", it)
            return english
        }
    }

    private fun containsChinese(input: String): Boolean {
        val pattern = Pattern.compile("[\\u4e00-\\u9fa5]")
        val matcher = pattern.matcher(input)
        return matcher.find()
    }

    private fun allWordsCapitalize(input: String): String {
        val exclusions: Set<String> = setOf("and", "but", "or", "nor", "for", "in", "on", "at", "of", "to", "from", "by", "the", "a", "an", "vs.")
        val pattern = Pattern.compile("\\b[\\w-]+\\b|[\\s,()]")
        val matcher = pattern.matcher(input)

        val result = StringBuilder()
        while (matcher.find()) {
            val part = matcher.group()
            var isIgnoreWord = false
            for (word in exclusions) {
                if (part.equals(word, ignoreCase = true)) {
                    isIgnoreWord = true
                    break
                }
            }
            if (!isIgnoreWord && part.matches("\\b[\\w-]+\\b".toRegex())) {
                // Capitalize the first letter of words not in the ignore list
                result.append(part[0].uppercaseChar()).append(part.substring(1))
            } else {
                // Keep ignore words and delimiters unchanged
                result.append(part)
            }
        }
        return result.toString()
    }

    private fun replaceFirstCharCapitalize(input: String): String {
        return input.replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() }
    }
}