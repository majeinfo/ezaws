FROM python:3.9-slim
LABEL maintainer="jd@maje.biz"
ARG target_dir=/appli
ADD requirements.txt ${target_dir}/
RUN apt-get update && apt-get install default-libmysqlclient-dev gcc git -y
RUN pip install -r ${target_dir}/requirements.txt
RUN cd ${target_dir} && git clone https://github.com/majeinfo/ezaws.git
#RUN apt-get autoremove gcc git -y
EXPOSE 8000
WORKDIR ${target_dir}/ezaws
CMD [ "/usr/local/bin/python", "manage.py", "runserver", "0.0.0.0:8000" ]
