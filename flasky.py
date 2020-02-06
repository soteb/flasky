# 个人注译版本

import os
from dotenv import load_dotenv

# “从 .env 文件中导入环境变量”
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# 测试代码覆盖率
# 可以将None赋值给任何变量，也可以给None值变量赋值
COV = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage
    COV = coverage.coverage(branch=True, include='app/*')
    COV.start()

# 数据库迁移
import sys
import click
from flask_migrate import Migrate, upgrade
from app import create_app, db
from app.models import User, Follow, Role, Permission, Post, Comment

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)

# “flask shell 命令将自动把这些对象导入 shell。”
# “每次启动 shell 会话都要导入数据库实例和模型”
# 函数的返回结果必须是dict，届时dict中的key将作为变量在所有"文件"中可见。
@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Follow=Follow, Role=Role,
                Permission=Permission, Post=Post, Comment=Comment)


@app.cli.command()
@click.option('--coverage/--no-coverage', default=False,
              help='Run tests under code coverage.')
@click.argument('test_names', nargs=-1)   # -1 可以多个参数
def test(coverage, test_names):
    """Run the unit tests."""
    if coverage and not os.environ.get('FLASK_COVERAGE'):
        import subprocess
        os.environ['FLASK_COVERAGE'] = '1'
        sys.exit(subprocess.call(sys.argv))

    import unittest
    if test_names:
        tests = unittest.TestLoader().loadTestsFromNames(test_names)
    else:
        tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)
    if COV:
        COV.stop()
        COV.save()
        print('Coverage Summary:')
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML version: file://%s/index.html' % covdir)
        COV.erase()

# 性能分析 源码分析
# 通过应用的 wsgi_app 属性，把 Werkzeug 的 ProfilerMiddleware 中间件依附到应用上。
# WSGI 中间件在 Web 服务器把请求分派给应用时调用，可用于修改处理请求的方式。这里通过中间件捕获分析数据。
# 注意，随后通过 app.run() 方法，以编程的方式启动应用。
@app.cli.command()
@click.option('--length', default=25,
              help='Number of functions to include in the profiler report.')
@click.option('--profile-dir', default=None,
              help='Directory where profiler data files are saved.')
def profile(length, profile_dir):
    """Start the application under the code profiler."""
    from werkzeug.contrib.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length],
                                      profile_dir=profile_dir)
    app.run()


# “应用安装到生产服务器上之后，都要执行一系列任务，其中就包括创建或更新数据库表。”
# 如果每次安装或升级应用都手动执行这些任务，那么会容易出错，也浪费时间。因此，可以在 flasky.py 中添加一个命令，自动执行全部任务。
@app.cli.command()
def deploy():
    """Run deployment tasks."""
    # “把数据库迁移到最新修订版本”
    upgrade()

    # “创建或更新用户角色”
    Role.insert_roles()

    # “确保所有用户都关注了他们自己”
    User.add_self_follows()
