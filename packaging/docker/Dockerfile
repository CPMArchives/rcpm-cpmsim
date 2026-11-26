FROM debian:bookworm-slim
ARG PACKAGE
COPY ${PACKAGE}/ /opt/rcpm-seed/
COPY packaging/docker/entrypoint.sh /usr/local/bin/rcpm-entrypoint
RUN chmod 755 /usr/local/bin/rcpm-entrypoint
VOLUME /data
EXPOSE 4000
ENTRYPOINT ["/usr/local/bin/rcpm-entrypoint"]
