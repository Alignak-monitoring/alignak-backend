uwsgi \
# Required on some distrib
#--plugin python \
--wsgi-file /home/alignak/app/webui/alignakwebui.py \
--callable app \
--socket 0.0.0.0:8868 \
--protocol=http \
--enable-threads

