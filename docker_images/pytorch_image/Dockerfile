FROM docker.io/pytorch/pytorch:1.5.1-cuda10.1-cudnn7-runtime

RUN apt-get update \
&& apt-get install -y sshfs curl \
&& python3 -m pip install --upgrade pip

# install connectors
RUN python3 -m pip install ipykernel && python3 -m ipykernel install --user && pip install papermill
RUN python3 -m pip install red-connector-ssh red-connector-http

# create user
RUN useradd -ms /bin/bash cc
USER cc

# install papermill wrapper
RUN mkdir -p "/home/cc/.local/bin" \
	&& curl https://raw.githubusercontent.com/curious-containers/cc-jupyter-service/master/cc_jupyter_service/papermill_wrapper.py > /home/cc/.local/bin/papermill_wrapper.py \
	&& chmod u+x /home/cc/.local/bin/papermill_wrapper.py

# set environment
ENV PATH="/home/cc/.local/bin:${PATH}"
ENV LC_ALL="C.UTF-8"
ENV LANG="C.UTF-8"
