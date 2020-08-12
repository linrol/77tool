DROP TABLE IF EXISTS "baseapp_bill_type" CASCADE;
CREATE TABLE "baseapp_bill_type"
(
    "id" VARCHAR(64),
    "code" VARCHAR(32) DEFAULT '',
    "name" VARCHAR(256) DEFAULT '',
    "bill_io_type_id" VARCHAR(64),
    "mapping_code" VARCHAR(64) DEFAULT '',
    "entry_src_system_id" VARCHAR(64) DEFAULT 'EntrySrcSystem.systemInput',
    "external_system_code" VARCHAR(128) DEFAULT '',
    "external_object_type" VARCHAR(128) DEFAULT '',
    "external_object_id" VARCHAR(128) DEFAULT '',
    "object_type" VARCHAR(64),
    "layout_template_id" VARCHAR(64),
    "print_template_id" VARCHAR(64),
    "mobile_template_id" VARCHAR(64),
    "is_to_menu" BOOLEAN DEFAULT false NOT NULL,
    "menu_name" VARCHAR(64) DEFAULT '',
    "menu_position_id" VARCHAR(64) DEFAULT '',
    "is_disabled" BOOLEAN DEFAULT false NOT NULL,
    "description" TEXT DEFAULT '',
    "created_user_id" VARCHAR(64),
    "created_time" TIMESTAMP,
    "modified_user_id" VARCHAR(64),
    "modified_time" TIMESTAMP,
    "code_seq" VARCHAR(64) DEFAULT '',
    "is_manual_code" BOOLEAN DEFAULT false NOT NULL,
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
COMMENT ON COLUMN "baseapp_bill_type"."code" IS '编码';
COMMENT ON COLUMN "baseapp_bill_type"."name" IS '名称';
COMMENT ON COLUMN "baseapp_bill_type"."bill_io_type_id" IS '单据方向';
COMMENT ON COLUMN "baseapp_bill_type"."mapping_code" IS '对照码';
COMMENT ON COLUMN "baseapp_bill_type"."entry_src_system_id" IS '数据来源类型';
COMMENT ON COLUMN "baseapp_bill_type"."external_system_code" IS '外部系统标识';
COMMENT ON COLUMN "baseapp_bill_type"."external_object_type" IS '外部系统对象类型';
COMMENT ON COLUMN "baseapp_bill_type"."external_object_id" IS '外部系统唯一标识';
COMMENT ON COLUMN "baseapp_bill_type"."object_type" IS '对象类型名称';
COMMENT ON COLUMN "baseapp_bill_type"."layout_template_id" IS '单据模板';
COMMENT ON COLUMN "baseapp_bill_type"."print_template_id" IS '单据打印模板';
COMMENT ON COLUMN "baseapp_bill_type"."mobile_template_id" IS '手机模板';
COMMENT ON COLUMN "baseapp_bill_type"."is_to_menu" IS '发布菜单';
COMMENT ON COLUMN "baseapp_bill_type"."menu_name" IS '菜单名称';
COMMENT ON COLUMN "baseapp_bill_type"."menu_position_id" IS '菜单位置';
COMMENT ON COLUMN "baseapp_bill_type"."is_disabled" IS '停用';
COMMENT ON COLUMN "baseapp_bill_type"."description" IS '说明';
COMMENT ON COLUMN "baseapp_bill_type"."created_user_id" IS '创建人';
COMMENT ON COLUMN "baseapp_bill_type"."created_time" IS '创建时间';
COMMENT ON COLUMN "baseapp_bill_type"."modified_user_id" IS '修改人';
COMMENT ON COLUMN "baseapp_bill_type"."modified_time" IS '修改时间';
COMMENT ON COLUMN "baseapp_bill_type"."code_seq" IS '流水编码';
COMMENT ON COLUMN "baseapp_bill_type"."is_manual_code" IS '编码手工输入';
COMMENT ON COLUMN "baseapp_bill_type"."is_system" IS '是否为系统数据';
COMMENT ON COLUMN "baseapp_bill_type"."is_init_data" IS '是否为预置数据';
COMMENT ON COLUMN "baseapp_bill_type"."is_deleted" IS '是否为删除数据';
COMMENT ON COLUMN "baseapp_bill_type"."data_version" IS '数据版本';
COMMENT ON COLUMN "baseapp_bill_type"."last_request_id" IS '最后一次更新请求的requestId';
COMMENT ON COLUMN "baseapp_bill_type"."last_modified_user_id" IS '最后修改人';
COMMENT ON COLUMN "baseapp_bill_type"."last_modified_time" IS '最后修改时间';
COMMENT ON COLUMN "baseapp_bill_type"."customized_fields" IS '自定义属性';
COMMENT ON TABLE "baseapp_bill_type" IS '单据类型';