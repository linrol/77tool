#!/bin/bash

set -e

dbName=""
test=""
fileName=""
while getopts ":d:f:h:p:w:" opt
do
	case $opt in
		d ) dbName=$OPTARG;;
		f ) fileName=$OPTARG;;
		h ) dbHost=$OPTARG;;
		p ) dbPort=$OPTARG;;
		w ) dbPass=$OPTARG;;
		? ) echo "unknow parameter $opt"
		    exit 1;;
	esac
done

dbUser=${DBUSER:-postgres}

PGPASSWORD=$dbPass psql -U $dbUser -h $dbHost -p $dbPort -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '$dbName' AND pid <> pg_backend_pid();"
PGPASSWORD=$dbPass pg_dump -U postgres -h $dbHost -p $dbPort -d $dbName -s -t baseapp_kanban_schema -t baseapp_kanban_definition -t baseapp_tab_definition -t baseapp_list_columns_schema_status_field -t baseapp_list_sort_item -t baseapp_list_sort_definition -t baseapp_list_columns_schema_sort_field -t baseapp_list_columns_schema_context_field -t baseapp_list_columns_schema -t baseapp_list_columns_definition -t baseapp_list_column_schema -t baseapp_list_column_group -t baseapp_list_column -t baseapp_query_schema -t baseapp_query_list_definition -t baseapp_query_item_schema -t baseapp_query_item -t baseapp_query_definition_group -t baseapp_query_definition | egrep -v "^--|^$|^SET|^CREATE TRIGGER|^GRANT SELECT" > $fileName.sql