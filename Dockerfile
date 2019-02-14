FROM continuumio/miniconda3

# Set the ENTRYPOINT to use bash
ENTRYPOINT ["/bin/bash", "-c"]

ENV PYTHONBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

COPY . /code/
WORKDIR /code/

EXPOSE 8000

RUN conda env create -f environment.yml
RUN echo "source activate jwql" > ~/.bashrc
ENV PATH /opt/conda/envs/jwql/bin:$PATH

CMD ["jwql/website/start.sh"]