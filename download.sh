#!/bin/bash

mkdir backend
cd backend
mkdir apps
cd apps
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/appx.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/allocation-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/allocation.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/arap-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/arap.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/asset-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/asset.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/baseapp-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/baseapp.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/base-common.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/base-common-test.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/basebi-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/basebi.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/biz-common.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/budget-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/budget.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/build.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/cashier-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/cashier.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/consolidation-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/consolidation.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/contract-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/contract.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/factgl-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/factgl.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/graphql.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/init-data.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/integration-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/integration.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/innertrans-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/innertrans.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/inv-common.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/inventory-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/inventory.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/invoice-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/invoice.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/procdesign-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/procdesign.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/project-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/project.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/purchase-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/purchase.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/reimbursement-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/reimbursement.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/salary-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/salary.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/projectcost-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/projectcost.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/sales-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/sales.git

cd ../
mkdir global
cd global
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/global/identity-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/global/identity.git

cd ../
mkdir platform
cd platform
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/platform/parent.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/platform/dbtools.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/platform/grpc-clients.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/platform/testapp.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/platform/sql-parser.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/platform/mbg-plugins.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/platform/json-schema-plugin.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/platform/metadata-impl.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/platform/metadata-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/platform/graphql-impl.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/platform/graphql-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/platform/common-base-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/platform/common-base.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/platform/app-common.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/platform/app-common-api.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/platform/app-build-plugins.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/platform/app-archetype.git

cd ../../
mkdir front
cd front
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/front/front-theory.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/front/front-goserver.git

cd ../
mkdir other
cd other
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/apps/qbos.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/apps/openapi.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/other/openapi-doc.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/apps/store.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/apps/jsf.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/other/qtms.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/other/emitter.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/apps/q7link-services.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/qip/idps.git
git clone http://backend-ci:${GIT_PASSWORD}@gitlab.q7link.com/backend/qip/qip-front.git

