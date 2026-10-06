FROM postgres:16.15-alpine@sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea

# El entrypoint oficial admite postgres sin root. Así gosu no es necesario
# y se elimina su runtime Go vulnerable, sin excepciones en el escáner.
RUN rm /usr/local/bin/gosu
USER postgres
