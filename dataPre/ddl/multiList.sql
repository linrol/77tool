
DROP TABLE IF EXISTS "baseapp_query_definition" CASCADE;
CREATE TABLE "baseapp_query_definition"
(
    "id" VARCHAR(64),
    "entry_src_system_id" VARCHAR(64) DEFAULT 'EntrySrcSystem.systemInput',
    "external_system_code" VARCHAR(128) DEFAULT '',
    "external_object_type" VARCHAR(128) DEFAULT '',
    "external_object_id" VARCHAR(128) DEFAULT '',
    "title" VARCHAR(64) DEFAULT '',
    "query_schema_id" VARCHAR(64),
    "is_public" BOOLEAN DEFAULT false NOT NULL,
    "object_type" VARCHAR(64),
    "seq_no" INTEGER DEFAULT 0 NOT NULL,
    "user_id" VARCHAR(64),
    "src_definition_id" VARCHAR(64),
    "public_definition_id" VARCHAR(64),
    "criteria_object" JSONB,
    "is_default" BOOLEAN DEFAULT false NOT NULL,
    "query_list_definition_id" VARCHAR(64),
    "created_user_id" VARCHAR(64),
    "created_time" TIMESTAMP,
    "modified_user_id" VARCHAR(64),
    "modified_time" TIMESTAMP,
    "is_system" BOOLEAN DEFAULT false NOT NULL,
    "is_init_data" BOOLEAN DEFAULT false NOT NULL,
    "is_deleted" BOOLEAN DEFAULT false NOT NULL,
    "data_version" BIGINT DEFAULT 0 NOT NULL,
    "last_request_id" VARCHAR(128) DEFAULT '',
    "last_modified_user_id" VARCHAR(64),
    "last_modified_time" TIMESTAMP,
    "customized_fields" JSONB,
    PRIMARY KEY ("id")
);
COMMENT ON COLUMN "baseapp_query_definition"."entry_src_system_id" IS '数据来源类型';
COMMENT ON COLUMN "baseapp_query_definition"."external_system_code" IS '外部系统标识';
COMMENT ON COLUMN "baseapp_query_definition"."external_object_type" IS '外部系统对象类型';
COMMENT ON COLUMN "baseapp_query_definition"."external_object_id" IS '外部系统唯一标识';
COMMENT ON COLUMN "baseapp_query_definition"."title" IS '标题';
COMMENT ON COLUMN "baseapp_query_definition"."query_schema_id" IS '查询方案模型id';
COMMENT ON COLUMN "baseapp_query_definition"."is_public" IS '是否是公共方案';
COMMENT ON COLUMN "baseapp_query_definition"."object_type" IS '对象类型';
COMMENT ON COLUMN "baseapp_query_definition"."seq_no" IS '排序';
COMMENT ON COLUMN "baseapp_query_definition"."user_id" IS '用户';
COMMENT ON COLUMN "baseapp_query_definition"."src_definition_id" IS '来源方案';
COMMENT ON COLUMN "baseapp_query_definition"."public_definition_id" IS '公共方案';
COMMENT ON COLUMN "baseapp_query_definition"."criteria_object" IS '记忆上次查询的 criteriaObject';
COMMENT ON COLUMN "baseapp_query_definition"."is_default" IS '默认查询方案';
COMMENT ON COLUMN "baseapp_query_definition"."query_list_definition_id" IS '查询列表方案id';
COMMENT ON COLUMN "baseapp_query_definition"."created_user_id" IS '创建人';
COMMENT ON COLUMN "baseapp_query_definition"."created_time" IS '创建时间';
COMMENT ON COLUMN "baseapp_query_definition"."modified_user_id" IS '修改人';
COMMENT ON COLUMN "baseapp_query_definition"."modified_time" IS '修改时间';
COMMENT ON COLUMN "baseapp_query_definition"."is_system" IS '是否是系统预置方案';
COMMENT ON COLUMN "baseapp_query_definition"."is_init_data" IS '是否为预置数据';
COMMENT ON COLUMN "baseapp_query_definition"."is_deleted" IS '是否为删除数据';
COMMENT ON COLUMN "baseapp_query_definition"."data_version" IS '数据版本';
COMMENT ON COLUMN "baseapp_query_definition"."last_request_id" IS '最后一次更新请求的requestId';
COMMENT ON COLUMN "baseapp_query_definition"."last_modified_user_id" IS '最后修改人';
COMMENT ON COLUMN "baseapp_query_definition"."last_modified_time" IS '最后修改时间';
COMMENT ON COLUMN "baseapp_query_definition"."customized_fields" IS '自定义属性';
COMMENT ON TABLE "baseapp_query_definition" IS '查询方案定义';
;

DROP TABLE IF EXISTS "baseapp_query_definition_group" CASCADE;
CREATE TABLE "baseapp_query_definition_group"
(
    "id" VARCHAR(64),
    "name" VARCHAR(128) DEFAULT '',
    "entry_src_system_id" VARCHAR(64) DEFAULT 'EntrySrcSystem.systemInput',
    "external_system_code" VARCHAR(128) DEFAULT '',
    "external_object_type" VARCHAR(128) DEFAULT '',
    "external_object_id" VARCHAR(128) DEFAULT '',
    "title" VARCHAR(32) DEFAULT '',
    "object_type" VARCHAR(64),
    "suppress_show_dialog" BOOLEAN DEFAULT false NOT NULL,
    "created_user_id" VARCHAR(64),
    "created_time" TIMESTAMP,
    "modified_user_id" VARCHAR(64),
    "modified_time" TIMESTAMP,
    "is_system" BOOLEAN DEFAULT false NOT NULL,
    "is_init_data" BOOLEAN DEFAULT false NOT NULL,
    "is_deleted" BOOLEAN DEFAULT false NOT NULL,
    "data_version" BIGINT DEFAULT 0 NOT NULL,
    "last_request_id" VARCHAR(128) DEFAULT '',
    "last_modified_user_id" VARCHAR(64),
    "last_modified_time" TIMESTAMP,
    "customized_fields" JSONB,
    PRIMARY KEY ("id")
);
COMMENT ON COLUMN "baseapp_query_definition_group"."name" IS '名称';
COMMENT ON COLUMN "baseapp_query_definition_group"."entry_src_system_id" IS '数据来源类型';
COMMENT ON COLUMN "baseapp_query_definition_group"."external_system_code" IS '外部系统标识';
COMMENT ON COLUMN "baseapp_query_definition_group"."external_object_type" IS '外部系统对象类型';
COMMENT ON COLUMN "baseapp_query_definition_group"."external_object_id" IS '外部系统唯一标识';
COMMENT ON COLUMN "baseapp_query_definition_group"."title" IS '标题';
COMMENT ON COLUMN "baseapp_query_definition_group"."object_type" IS '业务对象';
COMMENT ON COLUMN "baseapp_query_definition_group"."suppress_show_dialog" IS '抑制页面初始化时查询弹窗显示';
COMMENT ON COLUMN "baseapp_query_definition_group"."created_user_id" IS '创建人';
COMMENT ON COLUMN "baseapp_query_definition_group"."created_time" IS '创建时间';
COMMENT ON COLUMN "baseapp_query_definition_group"."modified_user_id" IS '修改人';
COMMENT ON COLUMN "baseapp_query_definition_group"."modified_time" IS '修改时间';
COMMENT ON COLUMN "baseapp_query_definition_group"."is_system" IS '是否为系统数据';
COMMENT ON COLUMN "baseapp_query_definition_group"."is_init_data" IS '是否为预置数据';
COMMENT ON COLUMN "baseapp_query_definition_group"."is_deleted" IS '是否为删除数据';
COMMENT ON COLUMN "baseapp_query_definition_group"."data_version" IS '数据版本';
COMMENT ON COLUMN "baseapp_query_definition_group"."last_request_id" IS '最后一次更新请求的requestId';
COMMENT ON COLUMN "baseapp_query_definition_group"."last_modified_user_id" IS '最后修改人';
COMMENT ON COLUMN "baseapp_query_definition_group"."last_modified_time" IS '最后修改时间';
COMMENT ON COLUMN "baseapp_query_definition_group"."customized_fields" IS '自定义属性';
COMMENT ON TABLE "baseapp_query_definition_group" IS '查询列表方案组';
CREATE UNIQUE INDEX "idx_baseapp_query_definition_group_querydefinitiongroup" ON "baseapp_query_definition_group" USING btree("name" ASC NULLS FIRST,"object_type" ASC NULLS FIRST) WHERE (is_deleted = false) and is_deleted = false;
COMMENT ON INDEX "idx_baseapp_query_definition_group_querydefinitiongroup" IS '关联的业务对象与name组成唯一索引';
;

DROP TABLE IF EXISTS "baseapp_query_item" CASCADE;
CREATE TABLE "baseapp_query_item"
(
    "id" VARCHAR(64),
    "ordinal" INTEGER DEFAULT 0 NOT NULL,
    "name" VARCHAR(256) DEFAULT '',
    "entry_src_system_id" VARCHAR(64) DEFAULT 'EntrySrcSystem.systemInput',
    "external_system_code" VARCHAR(128) DEFAULT '',
    "external_object_type" VARCHAR(128) DEFAULT '',
    "external_object_id" VARCHAR(128) DEFAULT '',
    "field_name" VARCHAR(256) DEFAULT '',
    "title" VARCHAR(256) DEFAULT '',
    "is_required" BOOLEAN DEFAULT false NOT NULL,
    "is_display" BOOLEAN DEFAULT false NOT NULL,
    "is_enabled" BOOLEAN DEFAULT false NOT NULL,
    "is_convenient" BOOLEAN DEFAULT false NOT NULL,
    "is_convenient_display" BOOLEAN DEFAULT false NOT NULL,
    "operator_id" VARCHAR(64),
    "is_auto_save" BOOLEAN DEFAULT false NOT NULL,
    "criteria_group" VARCHAR(128) DEFAULT '',
    "or_group" VARCHAR(64) DEFAULT '',
    "field_type" VARCHAR(64) DEFAULT '',
    "ref_object_type" VARCHAR(64),
    "ref_enum_type" VARCHAR(32) DEFAULT '',
    "is_virtual" BOOLEAN DEFAULT false NOT NULL,
    "last_criteria_value" JSONB,
    "is_extend" BOOLEAN DEFAULT false NOT NULL,
    "query_item_schema_id" VARCHAR(64),
    "query_definition_id" VARCHAR(64),
    "created_user_id" VARCHAR(64),
    "created_time" TIMESTAMP,
    "modified_user_id" VARCHAR(64),
    "modified_time" TIMESTAMP,
    "is_system" BOOLEAN DEFAULT false NOT NULL,
    "is_init_data" BOOLEAN DEFAULT false NOT NULL,
    "is_deleted" BOOLEAN DEFAULT false NOT NULL,
    "data_version" BIGINT DEFAULT 0 NOT NULL,
    "last_request_id" VARCHAR(128) DEFAULT '',
    "last_modified_user_id" VARCHAR(64),
    "last_modified_time" TIMESTAMP,
    "customized_fields" JSONB,
    PRIMARY KEY ("id")
);
COMMENT ON COLUMN "baseapp_query_item"."ordinal" IS '序号';
COMMENT ON COLUMN "baseapp_query_item"."name" IS '名称';
COMMENT ON COLUMN "baseapp_query_item"."entry_src_system_id" IS '数据来源类型';
COMMENT ON COLUMN "baseapp_query_item"."external_system_code" IS '外部系统标识';
COMMENT ON COLUMN "baseapp_query_item"."external_object_type" IS '外部系统对象类型';
COMMENT ON COLUMN "baseapp_query_item"."external_object_id" IS '外部系统唯一标识';
COMMENT ON COLUMN "baseapp_query_item"."field_name" IS '字段名称';
COMMENT ON COLUMN "baseapp_query_item"."title" IS '条件标题';
COMMENT ON COLUMN "baseapp_query_item"."is_required" IS '必填';
COMMENT ON COLUMN "baseapp_query_item"."is_display" IS '显示';
COMMENT ON COLUMN "baseapp_query_item"."is_enabled" IS '启用';
COMMENT ON COLUMN "baseapp_query_item"."is_convenient" IS '快捷条件';
COMMENT ON COLUMN "baseapp_query_item"."is_convenient_display" IS '快捷条件区显示';
COMMENT ON COLUMN "baseapp_query_item"."operator_id" IS '类型';
COMMENT ON COLUMN "baseapp_query_item"."is_auto_save" IS '自动记忆';
COMMENT ON COLUMN "baseapp_query_item"."criteria_group" IS '等价组';
COMMENT ON COLUMN "baseapp_query_item"."or_group" IS '逻辑或组';
COMMENT ON COLUMN "baseapp_query_item"."field_type" IS '字段类型';
COMMENT ON COLUMN "baseapp_query_item"."ref_object_type" IS '参照类型';
COMMENT ON COLUMN "baseapp_query_item"."ref_enum_type" IS '枚举类型';
COMMENT ON COLUMN "baseapp_query_item"."is_virtual" IS '是否是虚拟字段';
COMMENT ON COLUMN "baseapp_query_item"."last_criteria_value" IS '上次查询的值';
COMMENT ON COLUMN "baseapp_query_item"."is_extend" IS '是否是扩展字段';
COMMENT ON COLUMN "baseapp_query_item"."query_item_schema_id" IS '查询条件模型id';
COMMENT ON COLUMN "baseapp_query_item"."query_definition_id" IS '查询方案定义';
COMMENT ON COLUMN "baseapp_query_item"."created_user_id" IS '创建人';
COMMENT ON COLUMN "baseapp_query_item"."created_time" IS '创建时间';
COMMENT ON COLUMN "baseapp_query_item"."modified_user_id" IS '修改人';
COMMENT ON COLUMN "baseapp_query_item"."modified_time" IS '修改时间';
COMMENT ON COLUMN "baseapp_query_item"."is_system" IS '是否为系统数据';
COMMENT ON COLUMN "baseapp_query_item"."is_init_data" IS '是否为预置数据';
COMMENT ON COLUMN "baseapp_query_item"."is_deleted" IS '是否为删除数据';
COMMENT ON COLUMN "baseapp_query_item"."data_version" IS '数据版本';
COMMENT ON COLUMN "baseapp_query_item"."last_request_id" IS '最后一次更新请求的requestId';
COMMENT ON COLUMN "baseapp_query_item"."last_modified_user_id" IS '最后修改人';
COMMENT ON COLUMN "baseapp_query_item"."last_modified_time" IS '最后修改时间';
COMMENT ON COLUMN "baseapp_query_item"."customized_fields" IS '自定义属性';
COMMENT ON TABLE "baseapp_query_item" IS '查询条件';
;

DROP TABLE IF EXISTS "baseapp_query_item_schema" CASCADE;
CREATE TABLE "baseapp_query_item_schema"
(
    "id" VARCHAR(64),
    "ordinal" INTEGER DEFAULT 0 NOT NULL,
    "name" VARCHAR(256) DEFAULT '',
    "entry_src_system_id" VARCHAR(64) DEFAULT 'EntrySrcSystem.systemInput',
    "external_system_code" VARCHAR(128) DEFAULT '',
    "external_object_type" VARCHAR(128) DEFAULT '',
    "external_object_id" VARCHAR(128) DEFAULT '',
    "field_name" VARCHAR(256) DEFAULT '',
    "title" VARCHAR(256) DEFAULT '',
    "is_required" BOOLEAN DEFAULT false NOT NULL,
    "is_display" BOOLEAN DEFAULT false NOT NULL,
    "is_enabled" BOOLEAN DEFAULT false NOT NULL,
    "is_convenient" BOOLEAN DEFAULT false NOT NULL,
    "is_convenient_display" BOOLEAN DEFAULT false NOT NULL,
    "operator_id" VARCHAR(64),
    "is_auto_save" BOOLEAN DEFAULT false NOT NULL,
    "criteria_group" VARCHAR(128) DEFAULT '',
    "or_group" VARCHAR(64) DEFAULT '',
    "default_value" JSONB,
    "field_type" VARCHAR(64) DEFAULT '',
    "ref_object_type" VARCHAR(64),
    "ref_enum_type" VARCHAR(32) DEFAULT '',
    "query_fields" JSONB,
    "ref_additional_items" JSONB,
    "available_operators" JSONB,
    "disable_change_required" BOOLEAN DEFAULT false NOT NULL,
    "disable_change_display" BOOLEAN DEFAULT false NOT NULL,
    "disable_delete" BOOLEAN DEFAULT false NOT NULL,
    "disable_change_operator" BOOLEAN DEFAULT false NOT NULL,
    "is_virtual" BOOLEAN DEFAULT false NOT NULL,
    "query_schema_id" VARCHAR(64),
    "created_user_id" VARCHAR(64),
    "created_time" TIMESTAMP,
    "modified_user_id" VARCHAR(64),
    "modified_time" TIMESTAMP,
    "is_system" BOOLEAN DEFAULT false NOT NULL,
    "is_init_data" BOOLEAN DEFAULT false NOT NULL,
    "is_deleted" BOOLEAN DEFAULT false NOT NULL,
    "data_version" BIGINT DEFAULT 0 NOT NULL,
    "last_request_id" VARCHAR(128) DEFAULT '',
    "last_modified_user_id" VARCHAR(64),
    "last_modified_time" TIMESTAMP,
    "customized_fields" JSONB,
    PRIMARY KEY ("id")
);
COMMENT ON COLUMN "baseapp_query_item_schema"."ordinal" IS '序号';
COMMENT ON COLUMN "baseapp_query_item_schema"."name" IS '名称';
COMMENT ON COLUMN "baseapp_query_item_schema"."entry_src_system_id" IS '数据来源类型';
COMMENT ON COLUMN "baseapp_query_item_schema"."external_system_code" IS '外部系统标识';
COMMENT ON COLUMN "baseapp_query_item_schema"."external_object_type" IS '外部系统对象类型';
COMMENT ON COLUMN "baseapp_query_item_schema"."external_object_id" IS '外部系统唯一标识';
COMMENT ON COLUMN "baseapp_query_item_schema"."field_name" IS '字段名称';
COMMENT ON COLUMN "baseapp_query_item_schema"."title" IS '条件标题';
COMMENT ON COLUMN "baseapp_query_item_schema"."is_required" IS '必填';
COMMENT ON COLUMN "baseapp_query_item_schema"."is_display" IS '显示';
COMMENT ON COLUMN "baseapp_query_item_schema"."is_enabled" IS '启用';
COMMENT ON COLUMN "baseapp_query_item_schema"."is_convenient" IS '快捷条件';
COMMENT ON COLUMN "baseapp_query_item_schema"."is_convenient_display" IS '快捷条件区显示';
COMMENT ON COLUMN "baseapp_query_item_schema"."operator_id" IS '类型';
COMMENT ON COLUMN "baseapp_query_item_schema"."is_auto_save" IS '自动记忆';
COMMENT ON COLUMN "baseapp_query_item_schema"."criteria_group" IS '等价组';
COMMENT ON COLUMN "baseapp_query_item_schema"."or_group" IS '逻辑或组';
COMMENT ON COLUMN "baseapp_query_item_schema"."default_value" IS '默认值';
COMMENT ON COLUMN "baseapp_query_item_schema"."field_type" IS '字段类型';
COMMENT ON COLUMN "baseapp_query_item_schema"."ref_object_type" IS '参照类型';
COMMENT ON COLUMN "baseapp_query_item_schema"."ref_enum_type" IS '枚举类型';
COMMENT ON COLUMN "baseapp_query_item_schema"."query_fields" IS '查询字段';
COMMENT ON COLUMN "baseapp_query_item_schema"."ref_additional_items" IS '参照附加值';
COMMENT ON COLUMN "baseapp_query_item_schema"."available_operators" IS '可用类型';
COMMENT ON COLUMN "baseapp_query_item_schema"."disable_change_required" IS '禁止修改必填';
COMMENT ON COLUMN "baseapp_query_item_schema"."disable_change_display" IS '禁止修改显示';
COMMENT ON COLUMN "baseapp_query_item_schema"."disable_delete" IS '禁止删除';
COMMENT ON COLUMN "baseapp_query_item_schema"."disable_change_operator" IS '禁止修改类型';
COMMENT ON COLUMN "baseapp_query_item_schema"."is_virtual" IS '是否是虚拟字段';
COMMENT ON COLUMN "baseapp_query_item_schema"."query_schema_id" IS '查询方案模型id';
COMMENT ON COLUMN "baseapp_query_item_schema"."created_user_id" IS '创建人';
COMMENT ON COLUMN "baseapp_query_item_schema"."created_time" IS '创建时间';
COMMENT ON COLUMN "baseapp_query_item_schema"."modified_user_id" IS '修改人';
COMMENT ON COLUMN "baseapp_query_item_schema"."modified_time" IS '修改时间';
COMMENT ON COLUMN "baseapp_query_item_schema"."is_system" IS '是否为系统数据';
COMMENT ON COLUMN "baseapp_query_item_schema"."is_init_data" IS '是否为预置数据';
COMMENT ON COLUMN "baseapp_query_item_schema"."is_deleted" IS '是否为删除数据';
COMMENT ON COLUMN "baseapp_query_item_schema"."data_version" IS '数据版本';
COMMENT ON COLUMN "baseapp_query_item_schema"."last_request_id" IS '最后一次更新请求的requestId';
COMMENT ON COLUMN "baseapp_query_item_schema"."last_modified_user_id" IS '最后修改人';
COMMENT ON COLUMN "baseapp_query_item_schema"."last_modified_time" IS '最后修改时间';
COMMENT ON COLUMN "baseapp_query_item_schema"."customized_fields" IS '自定义属性';
COMMENT ON TABLE "baseapp_query_item_schema" IS '查询条件模型';
;

DROP TABLE IF EXISTS "baseapp_query_list_definition" CASCADE;
CREATE TABLE "baseapp_query_list_definition"
(
    "id" VARCHAR(64),
    "entry_src_system_id" VARCHAR(64) DEFAULT 'EntrySrcSystem.systemInput',
    "external_system_code" VARCHAR(128) DEFAULT '',
    "external_object_type" VARCHAR(128) DEFAULT '',
    "external_object_id" VARCHAR(128) DEFAULT '',
    "title" VARCHAR(64) DEFAULT '',
    "query_schema_id" VARCHAR(64) DEFAULT '',
    "is_public" BOOLEAN DEFAULT false NOT NULL,
    "seq_no" INTEGER DEFAULT 0 NOT NULL,
    "user_id" VARCHAR(64),
    "src_definition_id" VARCHAR(64),
    "public_definition_id" VARCHAR(64),
    "default_list_columns_def_id" VARCHAR(64),
    "support_master_and_details" BOOLEAN DEFAULT false NOT NULL,
    "group_id" VARCHAR(64),
    "object_type" VARCHAR(64),
    "created_user_id" VARCHAR(64),
    "created_time" TIMESTAMP,
    "modified_user_id" VARCHAR(64),
    "modified_time" TIMESTAMP,
    "is_system" BOOLEAN DEFAULT false NOT NULL,
    "is_init_data" BOOLEAN DEFAULT false NOT NULL,
    "is_deleted" BOOLEAN DEFAULT false NOT NULL,
    "data_version" BIGINT DEFAULT 0 NOT NULL,
    "last_request_id" VARCHAR(128) DEFAULT '',
    "last_modified_user_id" VARCHAR(64),
    "last_modified_time" TIMESTAMP,
    "customized_fields" JSONB,
    PRIMARY KEY ("id")
);
COMMENT ON COLUMN "baseapp_query_list_definition"."entry_src_system_id" IS '数据来源类型';
COMMENT ON COLUMN "baseapp_query_list_definition"."external_system_code" IS '外部系统标识';
COMMENT ON COLUMN "baseapp_query_list_definition"."external_object_type" IS '外部系统对象类型';
COMMENT ON COLUMN "baseapp_query_list_definition"."external_object_id" IS '外部系统唯一标识';
COMMENT ON COLUMN "baseapp_query_list_definition"."title" IS '标题';
COMMENT ON COLUMN "baseapp_query_list_definition"."query_schema_id" IS '查询模型id';
COMMENT ON COLUMN "baseapp_query_list_definition"."is_public" IS '是否是公共方案';
COMMENT ON COLUMN "baseapp_query_list_definition"."seq_no" IS '排序';
COMMENT ON COLUMN "baseapp_query_list_definition"."user_id" IS '用户';
COMMENT ON COLUMN "baseapp_query_list_definition"."src_definition_id" IS '来源方案';
COMMENT ON COLUMN "baseapp_query_list_definition"."public_definition_id" IS '公共方案';
COMMENT ON COLUMN "baseapp_query_list_definition"."default_list_columns_def_id" IS '默认的列表方案id';
COMMENT ON COLUMN "baseapp_query_list_definition"."support_master_and_details" IS '是否支持整单明细切换';
COMMENT ON COLUMN "baseapp_query_list_definition"."group_id" IS '查询列表组id';
COMMENT ON COLUMN "baseapp_query_list_definition"."object_type" IS '对象类型';
COMMENT ON COLUMN "baseapp_query_list_definition"."created_user_id" IS '创建人';
COMMENT ON COLUMN "baseapp_query_list_definition"."created_time" IS '创建时间';
COMMENT ON COLUMN "baseapp_query_list_definition"."modified_user_id" IS '修改人';
COMMENT ON COLUMN "baseapp_query_list_definition"."modified_time" IS '修改时间';
COMMENT ON COLUMN "baseapp_query_list_definition"."is_system" IS '是否是系统预置方案';
COMMENT ON COLUMN "baseapp_query_list_definition"."is_init_data" IS '是否为预置数据';
COMMENT ON COLUMN "baseapp_query_list_definition"."is_deleted" IS '是否为删除数据';
COMMENT ON COLUMN "baseapp_query_list_definition"."data_version" IS '数据版本';
COMMENT ON COLUMN "baseapp_query_list_definition"."last_request_id" IS '最后一次更新请求的requestId';
COMMENT ON COLUMN "baseapp_query_list_definition"."last_modified_user_id" IS '最后修改人';
COMMENT ON COLUMN "baseapp_query_list_definition"."last_modified_time" IS '最后修改时间';
COMMENT ON COLUMN "baseapp_query_list_definition"."customized_fields" IS '自定义属性';
COMMENT ON TABLE "baseapp_query_list_definition" IS '查询列表方案';
;

DROP TABLE IF EXISTS "baseapp_query_schema" CASCADE;
CREATE TABLE "baseapp_query_schema"
(
    "id" VARCHAR(64),
    "entry_src_system_id" VARCHAR(64) DEFAULT 'EntrySrcSystem.systemInput',
    "external_system_code" VARCHAR(128) DEFAULT '',
    "external_object_type" VARCHAR(128) DEFAULT '',
    "external_object_id" VARCHAR(128) DEFAULT '',
    "object_type" VARCHAR(64),
    "criteria" JSONB,
    "criteria_str" VARCHAR(512) DEFAULT '',
    "created_user_id" VARCHAR(64),
    "created_time" TIMESTAMP,
    "modified_user_id" VARCHAR(64),
    "modified_time" TIMESTAMP,
    "is_system" BOOLEAN DEFAULT false NOT NULL,
    "is_init_data" BOOLEAN DEFAULT false NOT NULL,
    "is_deleted" BOOLEAN DEFAULT false NOT NULL,
    "data_version" BIGINT DEFAULT 0 NOT NULL,
    "last_request_id" VARCHAR(128) DEFAULT '',
    "last_modified_user_id" VARCHAR(64),
    "last_modified_time" TIMESTAMP,
    "customized_fields" JSONB,
    PRIMARY KEY ("id")
);
COMMENT ON COLUMN "baseapp_query_schema"."entry_src_system_id" IS '数据来源类型';
COMMENT ON COLUMN "baseapp_query_schema"."external_system_code" IS '外部系统标识';
COMMENT ON COLUMN "baseapp_query_schema"."external_object_type" IS '外部系统对象类型';
COMMENT ON COLUMN "baseapp_query_schema"."external_object_id" IS '外部系统唯一标识';
COMMENT ON COLUMN "baseapp_query_schema"."object_type" IS '业务对象';
COMMENT ON COLUMN "baseapp_query_schema"."criteria" IS '固定查询条件';
COMMENT ON COLUMN "baseapp_query_schema"."criteria_str" IS '固定查询条件';
COMMENT ON COLUMN "baseapp_query_schema"."created_user_id" IS '创建人';
COMMENT ON COLUMN "baseapp_query_schema"."created_time" IS '创建时间';
COMMENT ON COLUMN "baseapp_query_schema"."modified_user_id" IS '修改人';
COMMENT ON COLUMN "baseapp_query_schema"."modified_time" IS '修改时间';
COMMENT ON COLUMN "baseapp_query_schema"."is_system" IS '是否为系统数据';
COMMENT ON COLUMN "baseapp_query_schema"."is_init_data" IS '是否为预置数据';
COMMENT ON COLUMN "baseapp_query_schema"."is_deleted" IS '是否为删除数据';
COMMENT ON COLUMN "baseapp_query_schema"."data_version" IS '数据版本';
COMMENT ON COLUMN "baseapp_query_schema"."last_request_id" IS '最后一次更新请求的requestId';
COMMENT ON COLUMN "baseapp_query_schema"."last_modified_user_id" IS '最后修改人';
COMMENT ON COLUMN "baseapp_query_schema"."last_modified_time" IS '最后修改时间';
COMMENT ON COLUMN "baseapp_query_schema"."customized_fields" IS '自定义属性';
COMMENT ON TABLE "baseapp_query_schema" IS '查询方案模型';
;



DROP TABLE IF EXISTS "baseapp_list_column" CASCADE;
CREATE TABLE "baseapp_list_column"
(
    "id" VARCHAR(64),
    "ordinal" INTEGER DEFAULT 0 NOT NULL,
    "name" VARCHAR(256) DEFAULT '',
    "entry_src_system_id" VARCHAR(64) DEFAULT 'EntrySrcSystem.systemInput',
    "external_system_code" VARCHAR(128) DEFAULT '',
    "external_object_type" VARCHAR(128) DEFAULT '',
    "external_object_id" VARCHAR(128) DEFAULT '',
    "list_columns_definition_id" VARCHAR(64),
    "field_name" VARCHAR(256) DEFAULT '',
    "field_type" VARCHAR(64) DEFAULT '',
    "ref_object_type" VARCHAR(64),
    "ref_enum_type" VARCHAR(32) DEFAULT '',
    "width" INTEGER DEFAULT 0 NOT NULL,
    "sort_direction_id" VARCHAR(64),
    "is_display" BOOLEAN DEFAULT false NOT NULL,
    "align" TEXT DEFAULT '',
    "fixed" TEXT DEFAULT '',
    "title" VARCHAR(256) DEFAULT '',
    "format" TEXT DEFAULT '',
    "is_total" BOOLEAN DEFAULT false NOT NULL,
    "aggr_func_name" VARCHAR(32) DEFAULT '',
    "list_column_group_id" VARCHAR(64),
    "expression" VARCHAR(512) DEFAULT '',
    "is_virtual" BOOLEAN DEFAULT false NOT NULL,
    "is_extend" BOOLEAN DEFAULT false NOT NULL,
    "list_column_schema_id" VARCHAR(64),
    "numeric_scale" INTEGER DEFAULT 0 NOT NULL,
    "length" INTEGER DEFAULT 0 NOT NULL,
    "created_user_id" VARCHAR(64),
    "created_time" TIMESTAMP,
    "modified_user_id" VARCHAR(64),
    "modified_time" TIMESTAMP,
    "is_system" BOOLEAN DEFAULT false NOT NULL,
    "is_init_data" BOOLEAN DEFAULT false NOT NULL,
    "is_deleted" BOOLEAN DEFAULT false NOT NULL,
    "data_version" BIGINT DEFAULT 0 NOT NULL,
    "last_request_id" VARCHAR(128) DEFAULT '',
    "last_modified_user_id" VARCHAR(64),
    "last_modified_time" TIMESTAMP,
    "customized_fields" JSONB,
    PRIMARY KEY ("id")
);
COMMENT ON COLUMN "baseapp_list_column"."ordinal" IS '序号';
COMMENT ON COLUMN "baseapp_list_column"."name" IS '名称';
COMMENT ON COLUMN "baseapp_list_column"."entry_src_system_id" IS '数据来源类型';
COMMENT ON COLUMN "baseapp_list_column"."external_system_code" IS '外部系统标识';
COMMENT ON COLUMN "baseapp_list_column"."external_object_type" IS '外部系统对象类型';
COMMENT ON COLUMN "baseapp_list_column"."external_object_id" IS '外部系统唯一标识';
COMMENT ON COLUMN "baseapp_list_column"."list_columns_definition_id" IS '列表定义';
COMMENT ON COLUMN "baseapp_list_column"."field_name" IS '字段名称';
COMMENT ON COLUMN "baseapp_list_column"."field_type" IS '字段类型';
COMMENT ON COLUMN "baseapp_list_column"."ref_object_type" IS '参照类型';
COMMENT ON COLUMN "baseapp_list_column"."ref_enum_type" IS '枚举类型';
COMMENT ON COLUMN "baseapp_list_column"."width" IS '宽度';
COMMENT ON COLUMN "baseapp_list_column"."sort_direction_id" IS '排序方式';
COMMENT ON COLUMN "baseapp_list_column"."is_display" IS '是否显示';
COMMENT ON COLUMN "baseapp_list_column"."align" IS '对齐方式';
COMMENT ON COLUMN "baseapp_list_column"."fixed" IS '锁定方向';
COMMENT ON COLUMN "baseapp_list_column"."title" IS '显示名称';
COMMENT ON COLUMN "baseapp_list_column"."format" IS '格式化';
COMMENT ON COLUMN "baseapp_list_column"."is_total" IS '是否显示合计';
COMMENT ON COLUMN "baseapp_list_column"."aggr_func_name" IS '聚合函数';
COMMENT ON COLUMN "baseapp_list_column"."list_column_group_id" IS '分组';
COMMENT ON COLUMN "baseapp_list_column"."expression" IS '表达式';
COMMENT ON COLUMN "baseapp_list_column"."is_virtual" IS '是否是虚拟字段';
COMMENT ON COLUMN "baseapp_list_column"."is_extend" IS '是否是扩展字段';
COMMENT ON COLUMN "baseapp_list_column"."list_column_schema_id" IS '栏目的模型id';
COMMENT ON COLUMN "baseapp_list_column"."numeric_scale" IS '小数精度';
COMMENT ON COLUMN "baseapp_list_column"."length" IS '长度';
COMMENT ON COLUMN "baseapp_list_column"."created_user_id" IS '创建人';
COMMENT ON COLUMN "baseapp_list_column"."created_time" IS '创建时间';
COMMENT ON COLUMN "baseapp_list_column"."modified_user_id" IS '修改人';
COMMENT ON COLUMN "baseapp_list_column"."modified_time" IS '修改时间';
COMMENT ON COLUMN "baseapp_list_column"."is_system" IS '是否为系统数据';
COMMENT ON COLUMN "baseapp_list_column"."is_init_data" IS '是否为预置数据';
COMMENT ON COLUMN "baseapp_list_column"."is_deleted" IS '是否为删除数据';
COMMENT ON COLUMN "baseapp_list_column"."data_version" IS '数据版本';
COMMENT ON COLUMN "baseapp_list_column"."last_request_id" IS '最后一次更新请求的requestId';
COMMENT ON COLUMN "baseapp_list_column"."last_modified_user_id" IS '最后修改人';
COMMENT ON COLUMN "baseapp_list_column"."last_modified_time" IS '最后修改时间';
COMMENT ON COLUMN "baseapp_list_column"."customized_fields" IS '自定义属性';
COMMENT ON TABLE "baseapp_list_column" IS '栏目';
;

DROP TABLE IF EXISTS "baseapp_list_column_group" CASCADE;
CREATE TABLE "baseapp_list_column_group"
(
    "id" VARCHAR(64),
    "ordinal" INTEGER DEFAULT 0 NOT NULL,
    "name" VARCHAR(128) DEFAULT '',
    "entry_src_system_id" VARCHAR(64) DEFAULT 'EntrySrcSystem.systemInput',
    "external_system_code" VARCHAR(128) DEFAULT '',
    "external_object_type" VARCHAR(128) DEFAULT '',
    "external_object_id" VARCHAR(128) DEFAULT '',
    "title" VARCHAR(256) DEFAULT '',
    "list_column_schema_id" VARCHAR(64),
    "list_columns_definition_id" VARCHAR(64),
    "created_user_id" VARCHAR(64),
    "created_time" TIMESTAMP,
    "modified_user_id" VARCHAR(64),
    "modified_time" TIMESTAMP,
    "is_system" BOOLEAN DEFAULT false NOT NULL,
    "is_init_data" BOOLEAN DEFAULT false NOT NULL,
    "is_deleted" BOOLEAN DEFAULT false NOT NULL,
    "data_version" BIGINT DEFAULT 0 NOT NULL,
    "last_request_id" VARCHAR(128) DEFAULT '',
    "last_modified_user_id" VARCHAR(64),
    "last_modified_time" TIMESTAMP,
    "customized_fields" JSONB,
    PRIMARY KEY ("id")
);
COMMENT ON COLUMN "baseapp_list_column_group"."ordinal" IS '序号';
COMMENT ON COLUMN "baseapp_list_column_group"."name" IS '分组名称';
COMMENT ON COLUMN "baseapp_list_column_group"."entry_src_system_id" IS '数据来源类型';
COMMENT ON COLUMN "baseapp_list_column_group"."external_system_code" IS '外部系统标识';
COMMENT ON COLUMN "baseapp_list_column_group"."external_object_type" IS '外部系统对象类型';
COMMENT ON COLUMN "baseapp_list_column_group"."external_object_id" IS '外部系统唯一标识';
COMMENT ON COLUMN "baseapp_list_column_group"."title" IS '显示名称';
COMMENT ON COLUMN "baseapp_list_column_group"."list_column_schema_id" IS '模型';
COMMENT ON COLUMN "baseapp_list_column_group"."list_columns_definition_id" IS '列表定义';
COMMENT ON COLUMN "baseapp_list_column_group"."created_user_id" IS '创建人';
COMMENT ON COLUMN "baseapp_list_column_group"."created_time" IS '创建时间';
COMMENT ON COLUMN "baseapp_list_column_group"."modified_user_id" IS '修改人';
COMMENT ON COLUMN "baseapp_list_column_group"."modified_time" IS '修改时间';
COMMENT ON COLUMN "baseapp_list_column_group"."is_system" IS '是否为系统数据';
COMMENT ON COLUMN "baseapp_list_column_group"."is_init_data" IS '是否为预置数据';
COMMENT ON COLUMN "baseapp_list_column_group"."is_deleted" IS '是否为删除数据';
COMMENT ON COLUMN "baseapp_list_column_group"."data_version" IS '数据版本';
COMMENT ON COLUMN "baseapp_list_column_group"."last_request_id" IS '最后一次更新请求的requestId';
COMMENT ON COLUMN "baseapp_list_column_group"."last_modified_user_id" IS '最后修改人';
COMMENT ON COLUMN "baseapp_list_column_group"."last_modified_time" IS '最后修改时间';
COMMENT ON COLUMN "baseapp_list_column_group"."customized_fields" IS '自定义属性';
COMMENT ON TABLE "baseapp_list_column_group" IS '分组表头';
;

DROP TABLE IF EXISTS "baseapp_list_column_schema" CASCADE;
CREATE TABLE "baseapp_list_column_schema"
(
    "id" VARCHAR(64),
    "ordinal" INTEGER DEFAULT 0 NOT NULL,
    "name" VARCHAR(256) DEFAULT '',
    "entry_src_system_id" VARCHAR(64) DEFAULT 'EntrySrcSystem.systemInput',
    "external_system_code" VARCHAR(128) DEFAULT '',
    "external_object_type" VARCHAR(128) DEFAULT '',
    "external_object_id" VARCHAR(128) DEFAULT '',
    "list_columns_schema_id" VARCHAR(64),
    "field_name" VARCHAR(256) DEFAULT '',
    "field_type" VARCHAR(32) DEFAULT '',
    "ref_object_type" VARCHAR(64),
    "ref_enum_type" VARCHAR(32) DEFAULT '',
    "width" INTEGER DEFAULT 0 NOT NULL,
    "sort" VARCHAR(64),
    "is_display" BOOLEAN DEFAULT false NOT NULL,
    "align" VARCHAR(64) DEFAULT '',
    "fixed" VARCHAR(64) DEFAULT '',
    "title" VARCHAR(256) DEFAULT '',
    "format" VARCHAR(256) DEFAULT '',
    "is_total" BOOLEAN DEFAULT false NOT NULL,
    "aggr_func_name" VARCHAR(32) DEFAULT '',
    "disable_change_visible" BOOLEAN DEFAULT false NOT NULL,
    "disable_delete" BOOLEAN DEFAULT false NOT NULL,
    "disable_change_sort" BOOLEAN DEFAULT false NOT NULL,
    "disable_change_size" BOOLEAN DEFAULT false NOT NULL,
    "expression" VARCHAR(512) DEFAULT '',
    "is_virtual" BOOLEAN DEFAULT false NOT NULL,
    "length" INTEGER DEFAULT 0 NOT NULL,
    "numeric_scale" INTEGER DEFAULT 0 NOT NULL,
    "created_user_id" VARCHAR(64),
    "created_time" TIMESTAMP,
    "modified_user_id" VARCHAR(64),
    "modified_time" TIMESTAMP,
    "is_system" BOOLEAN DEFAULT false NOT NULL,
    "is_init_data" BOOLEAN DEFAULT false NOT NULL,
    "is_deleted" BOOLEAN DEFAULT false NOT NULL,
    "data_version" BIGINT DEFAULT 0 NOT NULL,
    "last_request_id" VARCHAR(128) DEFAULT '',
    "last_modified_user_id" VARCHAR(64),
    "last_modified_time" TIMESTAMP,
    "customized_fields" JSONB,
    PRIMARY KEY ("id")
);
COMMENT ON COLUMN "baseapp_list_column_schema"."ordinal" IS '序号';
COMMENT ON COLUMN "baseapp_list_column_schema"."name" IS '名称';
COMMENT ON COLUMN "baseapp_list_column_schema"."entry_src_system_id" IS '数据来源类型';
COMMENT ON COLUMN "baseapp_list_column_schema"."external_system_code" IS '外部系统标识';
COMMENT ON COLUMN "baseapp_list_column_schema"."external_object_type" IS '外部系统对象类型';
COMMENT ON COLUMN "baseapp_list_column_schema"."external_object_id" IS '外部系统唯一标识';
COMMENT ON COLUMN "baseapp_list_column_schema"."list_columns_schema_id" IS '模型';
COMMENT ON COLUMN "baseapp_list_column_schema"."field_name" IS '字段名';
COMMENT ON COLUMN "baseapp_list_column_schema"."field_type" IS '字段类型';
COMMENT ON COLUMN "baseapp_list_column_schema"."ref_object_type" IS '参照类型';
COMMENT ON COLUMN "baseapp_list_column_schema"."ref_enum_type" IS '枚举类型';
COMMENT ON COLUMN "baseapp_list_column_schema"."width" IS '宽度';
COMMENT ON COLUMN "baseapp_list_column_schema"."sort" IS '排序';
COMMENT ON COLUMN "baseapp_list_column_schema"."is_display" IS '是否显示';
COMMENT ON COLUMN "baseapp_list_column_schema"."align" IS '对齐方式';
COMMENT ON COLUMN "baseapp_list_column_schema"."fixed" IS '锁定方向';
COMMENT ON COLUMN "baseapp_list_column_schema"."title" IS '显示名称';
COMMENT ON COLUMN "baseapp_list_column_schema"."format" IS '格式化';
COMMENT ON COLUMN "baseapp_list_column_schema"."is_total" IS '是否显示合计';
COMMENT ON COLUMN "baseapp_list_column_schema"."aggr_func_name" IS '是否停用';
COMMENT ON COLUMN "baseapp_list_column_schema"."disable_change_visible" IS '是否禁止用户修改显示';
COMMENT ON COLUMN "baseapp_list_column_schema"."disable_delete" IS '是否禁止用户删除';
COMMENT ON COLUMN "baseapp_list_column_schema"."disable_change_sort" IS '是否禁止用户修改排序';
COMMENT ON COLUMN "baseapp_list_column_schema"."disable_change_size" IS '是否禁止用户修改宽度';
COMMENT ON COLUMN "baseapp_list_column_schema"."expression" IS '表达式';
COMMENT ON COLUMN "baseapp_list_column_schema"."is_virtual" IS '是否虚拟字段';
COMMENT ON COLUMN "baseapp_list_column_schema"."length" IS '长度';
COMMENT ON COLUMN "baseapp_list_column_schema"."numeric_scale" IS '小数精度';
COMMENT ON COLUMN "baseapp_list_column_schema"."created_user_id" IS '创建人';
COMMENT ON COLUMN "baseapp_list_column_schema"."created_time" IS '创建时间';
COMMENT ON COLUMN "baseapp_list_column_schema"."modified_user_id" IS '修改人';
COMMENT ON COLUMN "baseapp_list_column_schema"."modified_time" IS '修改时间';
COMMENT ON COLUMN "baseapp_list_column_schema"."is_system" IS '是否为系统数据';
COMMENT ON COLUMN "baseapp_list_column_schema"."is_init_data" IS '是否为预置数据';
COMMENT ON COLUMN "baseapp_list_column_schema"."is_deleted" IS '是否为删除数据';
COMMENT ON COLUMN "baseapp_list_column_schema"."data_version" IS '数据版本';
COMMENT ON COLUMN "baseapp_list_column_schema"."last_request_id" IS '最后一次更新请求的requestId';
COMMENT ON COLUMN "baseapp_list_column_schema"."last_modified_user_id" IS '最后修改人';
COMMENT ON COLUMN "baseapp_list_column_schema"."last_modified_time" IS '最后修改时间';
COMMENT ON COLUMN "baseapp_list_column_schema"."customized_fields" IS '自定义属性';
COMMENT ON TABLE "baseapp_list_column_schema" IS '列表的栏目的模型';
;

DROP TABLE IF EXISTS "baseapp_list_columns_definition" CASCADE;
CREATE TABLE "baseapp_list_columns_definition"
(
    "id" VARCHAR(64),
    "ordinal" INTEGER DEFAULT 0 NOT NULL,
    "entry_src_system_id" VARCHAR(64) DEFAULT 'EntrySrcSystem.systemInput',
    "external_system_code" VARCHAR(128) DEFAULT '',
    "external_object_type" VARCHAR(128) DEFAULT '',
    "external_object_id" VARCHAR(128) DEFAULT '',
    "title" VARCHAR(256) DEFAULT '',
    "list_columns_schema_id" VARCHAR(64),
    "is_public" BOOLEAN DEFAULT false NOT NULL,
    "is_default" BOOLEAN DEFAULT false NOT NULL,
    "seq_no" INTEGER DEFAULT 0 NOT NULL,
    "page_size" INTEGER DEFAULT 0 NOT NULL,
    "user_id" VARCHAR(64),
    "src_definition_id" VARCHAR(64),
    "public_definition_id" VARCHAR(64),
    "is_master" BOOLEAN DEFAULT false NOT NULL,
    "query_list_definition_id" VARCHAR(64),
    "created_user_id" VARCHAR(64),
    "created_time" TIMESTAMP,
    "modified_user_id" VARCHAR(64),
    "modified_time" TIMESTAMP,
    "is_system" BOOLEAN DEFAULT false NOT NULL,
    "is_init_data" BOOLEAN DEFAULT false NOT NULL,
    "is_deleted" BOOLEAN DEFAULT false NOT NULL,
    "data_version" BIGINT DEFAULT 0 NOT NULL,
    "last_request_id" VARCHAR(128) DEFAULT '',
    "last_modified_user_id" VARCHAR(64),
    "last_modified_time" TIMESTAMP,
    "customized_fields" JSONB,
    PRIMARY KEY ("id")
);
COMMENT ON COLUMN "baseapp_list_columns_definition"."ordinal" IS '序号';
COMMENT ON COLUMN "baseapp_list_columns_definition"."entry_src_system_id" IS '数据来源类型';
COMMENT ON COLUMN "baseapp_list_columns_definition"."external_system_code" IS '外部系统标识';
COMMENT ON COLUMN "baseapp_list_columns_definition"."external_object_type" IS '外部系统对象类型';
COMMENT ON COLUMN "baseapp_list_columns_definition"."external_object_id" IS '外部系统唯一标识';
COMMENT ON COLUMN "baseapp_list_columns_definition"."title" IS '标题';
COMMENT ON COLUMN "baseapp_list_columns_definition"."list_columns_schema_id" IS '列表模型id';
COMMENT ON COLUMN "baseapp_list_columns_definition"."is_public" IS '是否是公共方案';
COMMENT ON COLUMN "baseapp_list_columns_definition"."is_default" IS '是否是默认方案';
COMMENT ON COLUMN "baseapp_list_columns_definition"."seq_no" IS '排序';
COMMENT ON COLUMN "baseapp_list_columns_definition"."page_size" IS '每页条数';
COMMENT ON COLUMN "baseapp_list_columns_definition"."user_id" IS '用户';
COMMENT ON COLUMN "baseapp_list_columns_definition"."src_definition_id" IS '来源方案';
COMMENT ON COLUMN "baseapp_list_columns_definition"."public_definition_id" IS '公共方案';
COMMENT ON COLUMN "baseapp_list_columns_definition"."is_master" IS '是否主表';
COMMENT ON COLUMN "baseapp_list_columns_definition"."query_list_definition_id" IS '查询列表方案id';
COMMENT ON COLUMN "baseapp_list_columns_definition"."created_user_id" IS '创建人';
COMMENT ON COLUMN "baseapp_list_columns_definition"."created_time" IS '创建时间';
COMMENT ON COLUMN "baseapp_list_columns_definition"."modified_user_id" IS '修改人';
COMMENT ON COLUMN "baseapp_list_columns_definition"."modified_time" IS '修改时间';
COMMENT ON COLUMN "baseapp_list_columns_definition"."is_system" IS '是否是系统预置方案';
COMMENT ON COLUMN "baseapp_list_columns_definition"."is_init_data" IS '是否为预置数据';
COMMENT ON COLUMN "baseapp_list_columns_definition"."is_deleted" IS '是否为删除数据';
COMMENT ON COLUMN "baseapp_list_columns_definition"."data_version" IS '数据版本';
COMMENT ON COLUMN "baseapp_list_columns_definition"."last_request_id" IS '最后一次更新请求的requestId';
COMMENT ON COLUMN "baseapp_list_columns_definition"."last_modified_user_id" IS '最后修改人';
COMMENT ON COLUMN "baseapp_list_columns_definition"."last_modified_time" IS '最后修改时间';
COMMENT ON COLUMN "baseapp_list_columns_definition"."customized_fields" IS '自定义属性';
COMMENT ON TABLE "baseapp_list_columns_definition" IS '列表方案';

DROP TABLE IF EXISTS "baseapp_list_columns_schema" CASCADE;
CREATE TABLE "baseapp_list_columns_schema"
(
    "id" VARCHAR(64),
    "entry_src_system_id" VARCHAR(64) DEFAULT 'EntrySrcSystem.systemInput',
    "external_system_code" VARCHAR(128) DEFAULT '',
    "external_object_type" VARCHAR(128) DEFAULT '',
    "external_object_id" VARCHAR(128) DEFAULT '',
    "title" VARCHAR(256) DEFAULT '',
    "object_type" VARCHAR(64),
    "numeric_scale" INTEGER DEFAULT 0 NOT NULL,
    "is_default" BOOLEAN DEFAULT false NOT NULL,
    "created_user_id" VARCHAR(64),
    "created_time" TIMESTAMP,
    "modified_user_id" VARCHAR(64),
    "modified_time" TIMESTAMP,
    "is_system" BOOLEAN DEFAULT false NOT NULL,
    "is_init_data" BOOLEAN DEFAULT false NOT NULL,
    "is_deleted" BOOLEAN DEFAULT false NOT NULL,
    "data_version" BIGINT DEFAULT 0 NOT NULL,
    "last_request_id" VARCHAR(128) DEFAULT '',
    "last_modified_user_id" VARCHAR(64),
    "last_modified_time" TIMESTAMP,
    "customized_fields" JSONB,
    PRIMARY KEY ("id")
);
COMMENT ON COLUMN "baseapp_list_columns_schema"."entry_src_system_id" IS '数据来源类型';
COMMENT ON COLUMN "baseapp_list_columns_schema"."external_system_code" IS '外部系统标识';
COMMENT ON COLUMN "baseapp_list_columns_schema"."external_object_type" IS '外部系统对象类型';
COMMENT ON COLUMN "baseapp_list_columns_schema"."external_object_id" IS '外部系统唯一标识';
COMMENT ON COLUMN "baseapp_list_columns_schema"."title" IS '标题';
COMMENT ON COLUMN "baseapp_list_columns_schema"."object_type" IS '业务对象';
COMMENT ON COLUMN "baseapp_list_columns_schema"."numeric_scale" IS '小数精度';
COMMENT ON COLUMN "baseapp_list_columns_schema"."is_default" IS '是否是默认方案';
COMMENT ON COLUMN "baseapp_list_columns_schema"."created_user_id" IS '创建人';
COMMENT ON COLUMN "baseapp_list_columns_schema"."created_time" IS '创建时间';
COMMENT ON COLUMN "baseapp_list_columns_schema"."modified_user_id" IS '修改人';
COMMENT ON COLUMN "baseapp_list_columns_schema"."modified_time" IS '修改时间';
COMMENT ON COLUMN "baseapp_list_columns_schema"."is_system" IS '是否为系统数据';
COMMENT ON COLUMN "baseapp_list_columns_schema"."is_init_data" IS '是否为预置数据';
COMMENT ON COLUMN "baseapp_list_columns_schema"."is_deleted" IS '是否为删除数据';
COMMENT ON COLUMN "baseapp_list_columns_schema"."data_version" IS '数据版本';
COMMENT ON COLUMN "baseapp_list_columns_schema"."last_request_id" IS '最后一次更新请求的requestId';
COMMENT ON COLUMN "baseapp_list_columns_schema"."last_modified_user_id" IS '最后修改人';
COMMENT ON COLUMN "baseapp_list_columns_schema"."last_modified_time" IS '最后修改时间';
COMMENT ON COLUMN "baseapp_list_columns_schema"."customized_fields" IS '自定义属性';
COMMENT ON TABLE "baseapp_list_columns_schema" IS '列表模型';

DROP TABLE IF EXISTS "baseapp_list_columns_schema_context_field" CASCADE;
CREATE TABLE "baseapp_list_columns_schema_context_field"
(
    "id" VARCHAR(64),
    "ordinal" INTEGER DEFAULT 0 NOT NULL,
    "entry_src_system_id" VARCHAR(64) DEFAULT 'EntrySrcSystem.systemInput',
    "external_system_code" VARCHAR(128) DEFAULT '',
    "external_object_type" VARCHAR(128) DEFAULT '',
    "external_object_id" VARCHAR(128) DEFAULT '',
    "field_name" VARCHAR(256) DEFAULT '',
    "list_column_schema_id" VARCHAR(64),
    "created_user_id" VARCHAR(64),
    "created_time" TIMESTAMP,
    "modified_user_id" VARCHAR(64),
    "modified_time" TIMESTAMP,
    "is_system" BOOLEAN DEFAULT false NOT NULL,
    "is_init_data" BOOLEAN DEFAULT false NOT NULL,
    "is_deleted" BOOLEAN DEFAULT false NOT NULL,
    "data_version" BIGINT DEFAULT 0 NOT NULL,
    "last_request_id" VARCHAR(128) DEFAULT '',
    "last_modified_user_id" VARCHAR(64),
    "last_modified_time" TIMESTAMP,
    "customized_fields" JSONB,
    PRIMARY KEY ("id")
);
COMMENT ON COLUMN "baseapp_list_columns_schema_context_field"."ordinal" IS '序号';
COMMENT ON COLUMN "baseapp_list_columns_schema_context_field"."entry_src_system_id" IS '数据来源类型';
COMMENT ON COLUMN "baseapp_list_columns_schema_context_field"."external_system_code" IS '外部系统标识';
COMMENT ON COLUMN "baseapp_list_columns_schema_context_field"."external_object_type" IS '外部系统对象类型';
COMMENT ON COLUMN "baseapp_list_columns_schema_context_field"."external_object_id" IS '外部系统唯一标识';
COMMENT ON COLUMN "baseapp_list_columns_schema_context_field"."field_name" IS '字段名';
COMMENT ON COLUMN "baseapp_list_columns_schema_context_field"."list_column_schema_id" IS '模型';
COMMENT ON COLUMN "baseapp_list_columns_schema_context_field"."created_user_id" IS '创建人';
COMMENT ON COLUMN "baseapp_list_columns_schema_context_field"."created_time" IS '创建时间';
COMMENT ON COLUMN "baseapp_list_columns_schema_context_field"."modified_user_id" IS '修改人';
COMMENT ON COLUMN "baseapp_list_columns_schema_context_field"."modified_time" IS '修改时间';
COMMENT ON COLUMN "baseapp_list_columns_schema_context_field"."is_system" IS '是否为系统数据';
COMMENT ON COLUMN "baseapp_list_columns_schema_context_field"."is_init_data" IS '是否为预置数据';
COMMENT ON COLUMN "baseapp_list_columns_schema_context_field"."is_deleted" IS '是否为删除数据';
COMMENT ON COLUMN "baseapp_list_columns_schema_context_field"."data_version" IS '数据版本';
COMMENT ON COLUMN "baseapp_list_columns_schema_context_field"."last_request_id" IS '最后一次更新请求的requestId';
COMMENT ON COLUMN "baseapp_list_columns_schema_context_field"."last_modified_user_id" IS '最后修改人';
COMMENT ON COLUMN "baseapp_list_columns_schema_context_field"."last_modified_time" IS '最后修改时间';
COMMENT ON COLUMN "baseapp_list_columns_schema_context_field"."customized_fields" IS '自定义属性';
COMMENT ON TABLE "baseapp_list_columns_schema_context_field" IS '列表的上下文字段';
;

DROP TABLE IF EXISTS "baseapp_list_columns_schema_sort_field" CASCADE;
CREATE TABLE "baseapp_list_columns_schema_sort_field"
(
    "id" VARCHAR(64),
    "ordinal" INTEGER DEFAULT 0 NOT NULL,
    "entry_src_system_id" VARCHAR(64) DEFAULT 'EntrySrcSystem.systemInput',
    "external_system_code" VARCHAR(128) DEFAULT '',
    "external_object_type" VARCHAR(128) DEFAULT '',
    "external_object_id" VARCHAR(128) DEFAULT '',
    "field_name" VARCHAR(256) DEFAULT '',
    "sort" VARCHAR(64),
    "list_column_schema_id" VARCHAR(64),
    "created_user_id" VARCHAR(64),
    "created_time" TIMESTAMP,
    "modified_user_id" VARCHAR(64),
    "modified_time" TIMESTAMP,
    "is_system" BOOLEAN DEFAULT false NOT NULL,
    "is_init_data" BOOLEAN DEFAULT false NOT NULL,
    "is_deleted" BOOLEAN DEFAULT false NOT NULL,
    "data_version" BIGINT DEFAULT 0 NOT NULL,
    "last_request_id" VARCHAR(128) DEFAULT '',
    "last_modified_user_id" VARCHAR(64),
    "last_modified_time" TIMESTAMP,
    "customized_fields" JSONB,
    PRIMARY KEY ("id")
);
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."ordinal" IS '序号';
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."entry_src_system_id" IS '数据来源类型';
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."external_system_code" IS '外部系统标识';
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."external_object_type" IS '外部系统对象类型';
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."external_object_id" IS '外部系统唯一标识';
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."field_name" IS '字段名';
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."sort" IS '排序';
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."list_column_schema_id" IS '模型';
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."created_user_id" IS '创建人';
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."created_time" IS '创建时间';
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."modified_user_id" IS '修改人';
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."modified_time" IS '修改时间';
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."is_system" IS '是否为系统数据';
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."is_init_data" IS '是否为预置数据';
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."is_deleted" IS '是否为删除数据';
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."data_version" IS '数据版本';
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."last_request_id" IS '最后一次更新请求的requestId';
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."last_modified_user_id" IS '最后修改人';
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."last_modified_time" IS '最后修改时间';
COMMENT ON COLUMN "baseapp_list_columns_schema_sort_field"."customized_fields" IS '自定义属性';
COMMENT ON TABLE "baseapp_list_columns_schema_sort_field" IS '列表的固定排序字段';
;