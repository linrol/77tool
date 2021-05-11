DROP TABLE IF EXISTS "baseapp_ui_config" CASCADE;
CREATE TABLE "baseapp_ui_config"
(
    "id" VARCHAR(64),
    "code" VARCHAR(32) DEFAULT '',
    "name" VARCHAR(256) DEFAULT '',
    "entry_src_system_id" VARCHAR(64) DEFAULT 'EntrySrcSystem.systemInput',
    "external_system_code" VARCHAR(128) DEFAULT '',
    "external_object_type" VARCHAR(128) DEFAULT '',
    "external_object_id" VARCHAR(128) DEFAULT '',
    "type" VARCHAR(64) DEFAULT '',
    "content" JSONB,
    "description" TEXT DEFAULT '',
    "is_disabled" BOOLEAN DEFAULT false NOT NULL,
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
COMMENT ON COLUMN "baseapp_ui_config"."code" IS '编码';
COMMENT ON COLUMN "baseapp_ui_config"."name" IS '名称';
COMMENT ON COLUMN "baseapp_ui_config"."entry_src_system_id" IS '数据来源类型';
COMMENT ON COLUMN "baseapp_ui_config"."external_system_code" IS '外部系统标识';
COMMENT ON COLUMN "baseapp_ui_config"."external_object_type" IS '外部系统对象类型';
COMMENT ON COLUMN "baseapp_ui_config"."external_object_id" IS '外部系统唯一标识';
COMMENT ON COLUMN "baseapp_ui_config"."type" IS '类别';
COMMENT ON COLUMN "baseapp_ui_config"."content" IS '内容';
COMMENT ON COLUMN "baseapp_ui_config"."description" IS '说明';
COMMENT ON COLUMN "baseapp_ui_config"."is_disabled" IS '停用';
COMMENT ON COLUMN "baseapp_ui_config"."created_user_id" IS '创建人';
COMMENT ON COLUMN "baseapp_ui_config"."created_time" IS '创建时间';
COMMENT ON COLUMN "baseapp_ui_config"."modified_user_id" IS '修改人';
COMMENT ON COLUMN "baseapp_ui_config"."modified_time" IS '修改时间';
COMMENT ON COLUMN "baseapp_ui_config"."is_system" IS '是否为系统数据';
COMMENT ON COLUMN "baseapp_ui_config"."is_init_data" IS '是否为预置数据';
COMMENT ON COLUMN "baseapp_ui_config"."is_deleted" IS '是否为删除数据';
COMMENT ON COLUMN "baseapp_ui_config"."data_version" IS '数据版本';
COMMENT ON COLUMN "baseapp_ui_config"."last_request_id" IS '最后一次更新请求的requestId';
COMMENT ON COLUMN "baseapp_ui_config"."last_modified_user_id" IS '最后修改人';
COMMENT ON COLUMN "baseapp_ui_config"."last_modified_time" IS '最后修改时间';
COMMENT ON COLUMN "baseapp_ui_config"."customized_fields" IS '自定义属性';
COMMENT ON TABLE "baseapp_ui_config" IS '前端配置';
;


DROP TABLE IF EXISTS "baseapp_bill_type_template" CASCADE;
CREATE TABLE "baseapp_bill_type_template"
(
    "id" VARCHAR(64),
    "created_org_id" VARCHAR(64),
    "code" VARCHAR(32) DEFAULT '',
    "name" VARCHAR(256) DEFAULT '',
    "bill_type_id" VARCHAR(64),
    "form_template_id" VARCHAR(64),
    "entry_src_system_id" VARCHAR(64) DEFAULT 'EntrySrcSystem.systemInput',
    "external_system_code" VARCHAR(128) DEFAULT '',
    "external_object_type" VARCHAR(128) DEFAULT '',
    "external_object_id" VARCHAR(128) DEFAULT '',
    "object_type" VARCHAR(64),
    "content" JSONB,
    "is_default" BOOLEAN DEFAULT false NOT NULL,
    "is_print" BOOLEAN DEFAULT false NOT NULL,
    "is_mobile" BOOLEAN DEFAULT false NOT NULL,
    "setting_level_id" VARCHAR(64),
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
COMMENT ON COLUMN "baseapp_bill_type_template"."code" IS '编码';
COMMENT ON COLUMN "baseapp_bill_type_template"."name" IS '名称';
COMMENT ON COLUMN "baseapp_bill_type_template"."bill_type_id" IS '单据模板业务类型';
COMMENT ON COLUMN "baseapp_bill_type_template"."entry_src_system_id" IS '数据来源类型';
COMMENT ON COLUMN "baseapp_bill_type_template"."external_system_code" IS '外部系统标识';
COMMENT ON COLUMN "baseapp_bill_type_template"."external_object_type" IS '外部系统对象类型';
COMMENT ON COLUMN "baseapp_bill_type_template"."external_object_id" IS '外部系统唯一标识';
COMMENT ON COLUMN "baseapp_bill_type_template"."object_type" IS '单据模板业务对象';
COMMENT ON COLUMN "baseapp_bill_type_template"."content" IS '模板内容';
COMMENT ON COLUMN "baseapp_bill_type_template"."is_default" IS '是否为默认';
COMMENT ON COLUMN "baseapp_bill_type_template"."is_print" IS '是否为打印模板';
COMMENT ON COLUMN "baseapp_bill_type_template"."is_mobile" IS '是否移动端模板';
COMMENT ON COLUMN "baseapp_bill_type_template"."created_user_id" IS '创建人';
COMMENT ON COLUMN "baseapp_bill_type_template"."created_time" IS '创建时间';
COMMENT ON COLUMN "baseapp_bill_type_template"."modified_user_id" IS '修改人';
COMMENT ON COLUMN "baseapp_bill_type_template"."modified_time" IS '修改时间';
COMMENT ON COLUMN "baseapp_bill_type_template"."is_system" IS '是否为系统模板';
COMMENT ON COLUMN "baseapp_bill_type_template"."is_init_data" IS '是否为预置数据';
COMMENT ON COLUMN "baseapp_bill_type_template"."is_deleted" IS '是否为删除数据';
COMMENT ON COLUMN "baseapp_bill_type_template"."data_version" IS '数据版本';
COMMENT ON COLUMN "baseapp_bill_type_template"."last_request_id" IS '最后一次更新请求的requestId';
COMMENT ON COLUMN "baseapp_bill_type_template"."last_modified_user_id" IS '最后修改人';
COMMENT ON COLUMN "baseapp_bill_type_template"."last_modified_time" IS '最后修改时间';
COMMENT ON COLUMN "baseapp_bill_type_template"."customized_fields" IS '自定义属性';
COMMENT ON TABLE "baseapp_bill_type_template" IS '单据子类型';
;