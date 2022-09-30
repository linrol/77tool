# amyTools

#### 介绍
企企使用python工具

#### 软件架构
软件架构说明


#### 安装教程

1.  xxxx
2.  xxxx
3.  xxxx

#### 使用说明

所有工具操作的工程均是branch/path.yaml中配置的工程，若有工程未配置，则不会操作未配置的工程
##1.changeVersion.py
####功能：
根据build工程的config.yaml文件将各工程版本号进行修改及开发脚本/接口数据修复文件清空
注：目前还不完善，只能修改framework版本、工程自身版本（除framework）、init-data版本。其他工程依赖版本尚无法修改。

####命令
python3 changeVersion.py 分支名称 [true]
true 代表是否清空开发脚本及接口数据修复文件

########例：
python3 changeVersion.py hotfix
根据hotfix分支的build工程config.yaml文件修改hotfix分支各工程依赖的其他工程版本以及自身版本

python3 changeVersion.py hotfix true
根据hotfix分支的build工程config.yaml文件修改hotfix分支各工程依赖的其他工程版本以及自身版本，最后清空开发脚本及接口数据修复文件

##2.checkanddeleted.py
####功能
获取拥有指定分支的工程，检查要删除的分支是否已合并至指定分支，若已合并则删除，如有工程未合并则所有工程均不进行删除。

####命令
python3 checkanddeleted.py 要删除的分支名称 合并的目标分支名称 [工程名称...]
########例：
python3 checkanddeleted.py hotfix master
检查所有工程hotfix分支是否已合并至master分支，若已合并则删除hotfix分支

python3 checkanddeleted.py hotfix none
不检查分支是否合并，直接删除所有工程的hotfix分支

python3 checkanddeleted.py hotfix master finance basebi
检查finance、basebi工程hotfix分支是否已合并至master分支，若已合并则删除finance、basebi的hotfix分支

##3.createBranch.py
####功能
根据来源分支创建目标分支，创建出来的分支，如果分支是hotfix/release/emergency/stage-emergency/hotfix-inte/dev，则会自动创建分支保护，所有工程只有管理员有全权限（mr、push）
####命令
python3 createBranch.py 来源分支1.来源分支2.来源分支3 目标分支[.检查目标分支是否存在] [工程名称...]
以来源分支为模板创建目标分支，只创建来源分支存在的工程，如果工程不存在来源分支，则不创建目标分支
来源分支支持.作为分隔符多个，优先匹配工程存在的首个来源分支为基准创建目标分支
检查目标分支是否存在：默认true。true:目标分支存在则报错，所有工程不创建分支;false:目标分支存在则不创建，不存在则创建
########例：
python3 createBranch.py master hotfix
基于master分支创建hotfix分支，并将hotfix进行分支保护，如果有工程存在hotfix分支则报错，并且所有工程均不创建目标分支

python3 createBranch.py master feature-xxx build finance
将build和finance工程，由master分支创建feature-xxx分支，如果build或finance存在hotfix分支则报错，并且不做创建操作

python3 createBranch.py master hotfix.false
基于master分支创建hotfix分支，并将hotfix进行分支保护，如果工程存在hotfix分支则忽略，工程不存在hotfix分支则创建hotfix分支

python3 createBranch.py stage-global.stage sprint20220929 app-common init-data
基于stage-global或stage分支创建sprint20220929分支，并将sprint20220929进行分支保护，如果工程不存在来源分支stage则基于stage-global创建

##4.protectBranch.py
####功能
对指定分支进行分支保护，权限命名依赖于最早的各分支权限控制规则
[hotfix权限]：build、init-data为管理员全权限（mr、push）；其余工程为管理员mr权限，所有人禁止push

[release权限]：所有工程管理员全权限（mr、push）

[dev权限]：所有工程所有人全权限（mr、push）

[none权限]：所有工程所有人禁止mr和push

[d]：删除分支保护

####命令
python3 protectBranch.py 分支 权限 [工程名称...]
########例：
python3 protectBranch.py hotfix release
将hotfix分支设置为release权限，一般在改版本号时修改为此权限

python3 protectBranch.py hotfix hotfix project budget
将project和budget工程的hotfix分支设置为hotfix权限，

python3 protectBranch.py hotfix d
将hotfix分支的分支保护删除

##5.checkcommit.py
####功能
检查指定分支的提交记录是否合并(cherry pick 或merge)到目标分支，并输出检查报告（输出地址：log/noMerge/）
####命令
python3 checkcommit.py 检查分支 目标分支 [偏移量，单位：天，默认10]
########例：
python3 checkcommit.py hotfix dev
检查10天内hotfix的提交记录是否均合并到dev分支

python3 checkcommit.py hotfix dev 3
检查3天内hotfix的提交记录是否均合并到dev分支

##6.checkout.py
####功能
检出指定分支代码
####命令
python3 checkout.py 分支1.分支2.分支3... [是否关闭IDEA的git管理]
分支：支持.作为分隔符多个，当工程不存在分支1时切换到分支2进行循环，直至找到工程存在的首个分支
是否关闭IDEA的git管理：默认false。false：不处理IDEA的git管理；true：将没有该分支的工程关闭IDEA git管理
注：由于idea的特性，在关闭前请将输入符焦点聚焦到有此分支的工程文件上。否则关闭git管理之后会有问题
########例：
python3 checkout.py hotfix
检出hotfix分支到本地

python3 checkout.py hotfix true
检出hotfix分支到本地，并关闭没有hotfix分支工程的idea git管理

python3 checkout.py sprint20220929.stage
检出sprint20220929分支到本地，当工程不存在sprint20220929分支时，检出工程的stage分支

##7.closeGit.py
####功能
关闭没有指定分支的工程的IDEA git管理
####命令
python3 closeGit.py 分支 
注：由于idea的特性，在关闭前请将输入符焦点聚焦到有此分支的工程文件上。否则关闭git管理之后会有问题
########例：
python3 closeGit.py hotfix
关闭没有hotfix分支工程的IDEA git管理

##8.tag.py
####功能
为指定分支最新提交打tag
####命令
python3 tag.py 分支 上线日期
####规则
1.build工程tag: 上线日期-分支
2.platform下的工程: framework的版本号-分支
3.其他工程: 工程自身版本号-分支
4.工程版本取自此分支的build工程中的config.yaml文件。如果build工程没有此分支则报错
5.如果tag存在则不打，platform下的工程如果最新提交上面有tag并且tag上记录的分支有此分支，则不打
########例：
python3 tag.py master 20210402
为master分支工程打tag

#### 参与贡献

1.  Fork 本仓库
2.  新建 Feat_xxx 分支
3.  提交代码
4.  新建 Pull Request


#### 码云特技

1.  使用 Readme\_XXX.md 来支持不同的语言，例如 Readme\_en.md, Readme\_zh.md
2.  码云官方博客 [blog.gitee.com](https://blog.gitee.com)
3.  你可以 [https://gitee.com/explore](https://gitee.com/explore) 这个地址来了解码云上的优秀开源项目
4.  [GVP](https://gitee.com/gvp) 全称是码云最有价值开源项目，是码云综合评定出的优秀开源项目
5.  码云官方提供的使用手册 [https://gitee.com/help](https://gitee.com/help)
6.  码云封面人物是一档用来展示码云会员风采的栏目 [https://gitee.com/gitee-stars/](https://gitee.com/gitee-stars/)
