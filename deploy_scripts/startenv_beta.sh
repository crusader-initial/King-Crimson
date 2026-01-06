echo "conda环境和依赖安装开始"


export PATH="/home/q/www/miniconda3/bin:$PATH"
conda init bash
source ~/.bashrc


conda -version
conda activate py311
python --version
echo "conda切换结束"


python /home/q/www/pf_king_crimson/webapps/ROOT/run.py

export AUTO_ENV_NAME="beta"

export RUN_CMD="python server.py"

export GUNICORN_PATH="gunicorn"