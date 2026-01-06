echo "conda环境和依赖安装开始"


export PATH="/home/q/www/miniconda3/bin:$PATH"
conda init bash
source ~/.bashrc
conda activate py311

echo "conda切换结束"

pip install -r requirements.txt -i http://devpi.corp.qunar.com/qunar/dev/+simple/ --trusted-host devpi.corp.qunar.com

export AUTO_ENV_NAME="beta"

export RUN_CMD="python server.py"

export GUNICORN_PATH="gunicorn"