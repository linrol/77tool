#!/bin/bash

set -e

dbName=""
test=""
fileName=""
while getopts ":d:f:h:p:" opt
do
	case $opt in
		d ) dbName=$OPTARG;;
		f ) fileName=$OPTARG;;
		h ) dbHost=$OPTARG;;
		p ) dbPort=$OPTARG;;
		? ) echo "unknow parameter $opt"
		    exit 1;;
	esac
done

dbHost=${DBHOST:-localhost}
dbPort=${DBPORT:-5432}
dbUser=${DBUSER:-postgres}
dbPass=${DBPASS:-123}
dbName=${DBNAME:-preset}

if [ "$fileName" = "" ]; then
	echo "-d <db name> needed"
	exit 1
fi


PGPASSWORD=$dbPass psql -U $dbUser -h $dbHost -p $dbPort -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '$dbName' AND pid <> pg_backend_pid();"
PGPASSWORD=$dbPass psql -U $dbUser -h $dbHost -p $dbPort -c "DROP DATABASE IF EXISTS \"$dbName\";"
PGPASSWORD=$dbPass psql -U $dbUser -h $dbHost -p $dbPort -c "CREATE DATABASE \"$dbName\" WITH OWNER=\"$dbUser\";"

PGOPTIONS='--client-min-messages=warning' PGPASSWORD=$dbPass psql -U $dbUser $params -d $dbName -f $fileName.sql -v ON_ERROR_STOP=1