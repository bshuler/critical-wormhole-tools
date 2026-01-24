FROM nginx:1.25-bookworm AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpcre3-dev \
    zlib1g-dev \
    libssl-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Download nginx source (same version as base image)
WORKDIR /tmp
RUN wget http://nginx.org/download/nginx-1.25.5.tar.gz \
    && tar -xzf nginx-1.25.5.tar.gz

# Copy module source files
COPY ngx_http_wormhole_module.c /tmp/nginx-1.25.5/
COPY config /tmp/nginx-1.25.5/

# Build nginx with the wormhole module as a dynamic module
WORKDIR /tmp/nginx-1.25.5
RUN ./configure \
    --with-compat \
    --add-dynamic-module=. \
    --with-cc-opt='-g -O2' \
    && make modules

# Production image
FROM nginx:1.25-bookworm

# Copy compiled module
COPY --from=builder /tmp/nginx-1.25.5/objs/ngx_http_wormhole_module.so /etc/nginx/modules/

# Copy test configuration
COPY test/nginx.conf /etc/nginx/nginx.conf

# Load the wormhole module
RUN sed -i '1i load_module /etc/nginx/modules/ngx_http_wormhole_module.so;' /etc/nginx/nginx.conf

# Verify module loads successfully
RUN nginx -t

# Expose HTTP port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
