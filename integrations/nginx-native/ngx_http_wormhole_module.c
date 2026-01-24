/*
 * ngx_http_wormhole_module.c - Native Nginx module for Wormhole Name System
 *
 * This module integrates WNS resolution directly into Nginx by communicating
 * with the wh daemon API. It intercepts requests for wh:// URLs and .wns
 * domains, resolves them via the daemon, and proxies the connection.
 *
 * Configuration example:
 *   location / {
 *       wormhole_enable on;
 *       wormhole_daemon http://localhost:8080;
 *       wormhole_identity default;
 *       wormhole_timeout 30s;
 *   }
 */

#include <ngx_config.h>
#include <ngx_core.h>
#include <ngx_http.h>

/* Module configuration structure */
typedef struct {
    ngx_flag_t      enable;           /* wormhole_enable on/off */
    ngx_str_t       daemon_url;       /* wormhole_daemon URL */
    ngx_str_t       identity;         /* wormhole_identity name */
    ngx_str_t       relay_url;        /* wormhole_relay URL */
    ngx_msec_t      timeout;          /* wormhole_timeout */
    ngx_msec_t      connect_timeout;  /* wormhole_connect_timeout */
    size_t          cache_size;       /* wormhole_cache_size */
    ngx_msec_t      cache_time;       /* wormhole_cache_time */
} ngx_http_wormhole_loc_conf_t;

/* Upstream request context */
typedef struct {
    ngx_http_request_t  *request;
    ngx_str_t            wns_name;
    ngx_str_t            original_uri;
    ngx_int_t            status;
} ngx_http_wormhole_ctx_t;

/* Forward declarations */
static ngx_int_t ngx_http_wormhole_handler(ngx_http_request_t *r);
static void *ngx_http_wormhole_create_loc_conf(ngx_conf_t *cf);
static char *ngx_http_wormhole_merge_loc_conf(ngx_conf_t *cf, void *parent, void *child);
static ngx_int_t ngx_http_wormhole_init(ngx_conf_t *cf);
static ngx_int_t is_wormhole_request(ngx_http_request_t *r, ngx_str_t *name);
static ngx_int_t ngx_http_wormhole_proxy_to_daemon(ngx_http_request_t *r,
    ngx_http_wormhole_loc_conf_t *conf, ngx_str_t *wns_name);

/* Configuration directives */
static ngx_command_t ngx_http_wormhole_commands[] = {
    {
        ngx_string("wormhole_enable"),
        NGX_HTTP_MAIN_CONF|NGX_HTTP_SRV_CONF|NGX_HTTP_LOC_CONF|NGX_CONF_FLAG,
        ngx_conf_set_flag_slot,
        NGX_HTTP_LOC_CONF_OFFSET,
        offsetof(ngx_http_wormhole_loc_conf_t, enable),
        NULL
    },
    {
        ngx_string("wormhole_daemon"),
        NGX_HTTP_MAIN_CONF|NGX_HTTP_SRV_CONF|NGX_HTTP_LOC_CONF|NGX_CONF_TAKE1,
        ngx_conf_set_str_slot,
        NGX_HTTP_LOC_CONF_OFFSET,
        offsetof(ngx_http_wormhole_loc_conf_t, daemon_url),
        NULL
    },
    {
        ngx_string("wormhole_identity"),
        NGX_HTTP_MAIN_CONF|NGX_HTTP_SRV_CONF|NGX_HTTP_LOC_CONF|NGX_CONF_TAKE1,
        ngx_conf_set_str_slot,
        NGX_HTTP_LOC_CONF_OFFSET,
        offsetof(ngx_http_wormhole_loc_conf_t, identity),
        NULL
    },
    {
        ngx_string("wormhole_relay"),
        NGX_HTTP_MAIN_CONF|NGX_HTTP_SRV_CONF|NGX_HTTP_LOC_CONF|NGX_CONF_TAKE1,
        ngx_conf_set_str_slot,
        NGX_HTTP_LOC_CONF_OFFSET,
        offsetof(ngx_http_wormhole_loc_conf_t, relay_url),
        NULL
    },
    {
        ngx_string("wormhole_timeout"),
        NGX_HTTP_MAIN_CONF|NGX_HTTP_SRV_CONF|NGX_HTTP_LOC_CONF|NGX_CONF_TAKE1,
        ngx_conf_set_msec_slot,
        NGX_HTTP_LOC_CONF_OFFSET,
        offsetof(ngx_http_wormhole_loc_conf_t, timeout),
        NULL
    },
    {
        ngx_string("wormhole_connect_timeout"),
        NGX_HTTP_MAIN_CONF|NGX_HTTP_SRV_CONF|NGX_HTTP_LOC_CONF|NGX_CONF_TAKE1,
        ngx_conf_set_msec_slot,
        NGX_HTTP_LOC_CONF_OFFSET,
        offsetof(ngx_http_wormhole_loc_conf_t, connect_timeout),
        NULL
    },

    ngx_null_command
};

/* Module context */
static ngx_http_module_t ngx_http_wormhole_module_ctx = {
    NULL,                                   /* preconfiguration */
    ngx_http_wormhole_init,                 /* postconfiguration */
    NULL,                                   /* create main configuration */
    NULL,                                   /* init main configuration */
    NULL,                                   /* create server configuration */
    NULL,                                   /* merge server configuration */
    ngx_http_wormhole_create_loc_conf,      /* create location configuration */
    ngx_http_wormhole_merge_loc_conf        /* merge location configuration */
};

/* Module definition */
ngx_module_t ngx_http_wormhole_module = {
    NGX_MODULE_V1,
    &ngx_http_wormhole_module_ctx,          /* module context */
    ngx_http_wormhole_commands,             /* module directives */
    NGX_HTTP_MODULE,                        /* module type */
    NULL,                                   /* init master */
    NULL,                                   /* init module */
    NULL,                                   /* init process */
    NULL,                                   /* init thread */
    NULL,                                   /* exit thread */
    NULL,                                   /* exit process */
    NULL,                                   /* exit master */
    NGX_MODULE_V1_PADDING
};

/*
 * Create location configuration
 */
static void *
ngx_http_wormhole_create_loc_conf(ngx_conf_t *cf)
{
    ngx_http_wormhole_loc_conf_t *conf;

    conf = ngx_pcalloc(cf->pool, sizeof(ngx_http_wormhole_loc_conf_t));
    if (conf == NULL) {
        return NULL;
    }

    conf->enable = NGX_CONF_UNSET;
    conf->timeout = NGX_CONF_UNSET_MSEC;
    conf->connect_timeout = NGX_CONF_UNSET_MSEC;
    conf->cache_size = NGX_CONF_UNSET_SIZE;
    conf->cache_time = NGX_CONF_UNSET_MSEC;

    return conf;
}

/*
 * Merge location configuration
 */
static char *
ngx_http_wormhole_merge_loc_conf(ngx_conf_t *cf, void *parent, void *child)
{
    ngx_http_wormhole_loc_conf_t *prev = parent;
    ngx_http_wormhole_loc_conf_t *conf = child;

    ngx_conf_merge_value(conf->enable, prev->enable, 0);

    ngx_conf_merge_str_value(conf->daemon_url, prev->daemon_url, "http://localhost:8080");
    ngx_conf_merge_str_value(conf->identity, prev->identity, "default");
    ngx_conf_merge_str_value(conf->relay_url, prev->relay_url, "");

    ngx_conf_merge_msec_value(conf->timeout, prev->timeout, 30000);
    ngx_conf_merge_msec_value(conf->connect_timeout, prev->connect_timeout, 10000);
    ngx_conf_merge_size_value(conf->cache_size, prev->cache_size, 100 * 1024 * 1024);
    ngx_conf_merge_msec_value(conf->cache_time, prev->cache_time, 300000);

    return NGX_CONF_OK;
}

/*
 * Check if request is for a wormhole URL
 *
 * Detects wormhole requests by checking:
 * 1. Host header starts with "wh://"
 * 2. Host header ends with ".wns"
 * 3. X-Wormhole-Name header is present
 *
 * Returns 1 if wormhole request, 0 otherwise.
 * Sets name to the WNS name to resolve.
 */
static ngx_int_t
is_wormhole_request(ngx_http_request_t *r, ngx_str_t *name)
{
    ngx_table_elt_t  *h;
    ngx_list_part_t  *part;
    u_char           *host;
    size_t            len;
    ngx_uint_t        i;

    /* Check for X-Wormhole-Name header first */
    part = &r->headers_in.headers.part;
    h = part->elts;

    for (i = 0; /* void */; i++) {
        if (i >= part->nelts) {
            if (part->next == NULL) {
                break;
            }
            part = part->next;
            h = part->elts;
            i = 0;
        }

        if (h[i].key.len == 15 &&
            ngx_strncasecmp(h[i].key.data, (u_char *)"X-Wormhole-Name", 15) == 0)
        {
            name->data = h[i].value.data;
            name->len = h[i].value.len;
            ngx_log_error(NGX_LOG_DEBUG, r->connection->log, 0,
                          "wormhole: found X-Wormhole-Name header: %V", name);
            return 1;
        }
    }

    /* Check Host header */
    if (r->headers_in.host == NULL) {
        return 0;
    }

    host = r->headers_in.host->value.data;
    len = r->headers_in.host->value.len;

    /* Check for wh:// prefix (browser might preserve scheme in Host) */
    if (len > 5 && ngx_strncasecmp(host, (u_char *)"wh://", 5) == 0) {
        name->data = host + 5;
        name->len = len - 5;

        /* Strip trailing port if present */
        for (i = 0; i < name->len; i++) {
            if (name->data[i] == ':') {
                name->len = i;
                break;
            }
        }

        ngx_log_error(NGX_LOG_DEBUG, r->connection->log, 0,
                      "wormhole: detected wh:// prefix, name: %V", name);
        return 1;
    }

    /* Check for .wns suffix */
    if (len > 4 && ngx_strncasecmp(host + len - 4, (u_char *)".wns", 4) == 0) {
        name->data = host;
        name->len = len;

        /* Strip trailing port if present */
        for (i = 0; i < name->len; i++) {
            if (name->data[i] == ':') {
                name->len = i;
                break;
            }
        }

        ngx_log_error(NGX_LOG_DEBUG, r->connection->log, 0,
                      "wormhole: detected .wns suffix, name: %V", name);
        return 1;
    }

    /* Check for .wormhole suffix */
    if (len > 9 && ngx_strncasecmp(host + len - 9, (u_char *)".wormhole", 9) == 0) {
        name->data = host;
        name->len = len;

        /* Strip trailing port if present */
        for (i = 0; i < name->len; i++) {
            if (name->data[i] == ':') {
                name->len = i;
                break;
            }
        }

        ngx_log_error(NGX_LOG_DEBUG, r->connection->log, 0,
                      "wormhole: detected .wormhole suffix, name: %V", name);
        return 1;
    }

    return 0;
}

/*
 * Build the proxy URI for the daemon's /browse endpoint
 *
 * The daemon expects: /browse/{name}{path}
 * For example: /browse/alice.wns/api/data
 */
static ngx_int_t
ngx_http_wormhole_build_proxy_uri(ngx_http_request_t *r, ngx_str_t *wns_name,
    ngx_str_t *proxy_uri)
{
    u_char  *p;
    size_t   len;

    /* Calculate length: "/browse/" + name + uri */
    len = sizeof("/browse/") - 1 + wns_name->len + r->uri.len;

    /* Handle query string if present */
    if (r->args.len > 0) {
        len += 1 + r->args.len;  /* "?" + args */
    }

    proxy_uri->data = ngx_pnalloc(r->pool, len);
    if (proxy_uri->data == NULL) {
        return NGX_ERROR;
    }

    p = ngx_cpymem(proxy_uri->data, "/browse/", sizeof("/browse/") - 1);
    p = ngx_cpymem(p, wns_name->data, wns_name->len);
    p = ngx_cpymem(p, r->uri.data, r->uri.len);

    if (r->args.len > 0) {
        *p++ = '?';
        p = ngx_cpymem(p, r->args.data, r->args.len);
    }

    proxy_uri->len = p - proxy_uri->data;

    ngx_log_error(NGX_LOG_DEBUG, r->connection->log, 0,
                  "wormhole: built proxy URI: %V", proxy_uri);

    return NGX_OK;
}

/*
 * Proxy the request to the wormhole daemon
 *
 * This creates an internal redirect to the daemon's /browse endpoint.
 * The daemon handles WNS resolution and connection establishment.
 */
static ngx_int_t
ngx_http_wormhole_proxy_to_daemon(ngx_http_request_t *r,
    ngx_http_wormhole_loc_conf_t *conf, ngx_str_t *wns_name)
{
    ngx_http_wormhole_ctx_t  *ctx;
    ngx_str_t                 proxy_uri;
    ngx_str_t                 daemon_host;
    ngx_url_t                 u;
    u_char                   *p;
    size_t                    len;

    /* Create module context */
    ctx = ngx_pcalloc(r->pool, sizeof(ngx_http_wormhole_ctx_t));
    if (ctx == NULL) {
        return NGX_HTTP_INTERNAL_SERVER_ERROR;
    }

    ctx->request = r;
    ctx->wns_name = *wns_name;
    ctx->original_uri = r->uri;
    ctx->status = 0;

    ngx_http_set_ctx(r, ctx, ngx_http_wormhole_module);

    /* Build the proxy URI */
    if (ngx_http_wormhole_build_proxy_uri(r, wns_name, &proxy_uri) != NGX_OK) {
        return NGX_HTTP_INTERNAL_SERVER_ERROR;
    }

    /* Parse daemon URL to extract host for proxy_pass style redirect */
    ngx_memzero(&u, sizeof(ngx_url_t));
    u.url = conf->daemon_url;
    u.no_resolve = 1;

    if (ngx_parse_url(r->pool, &u) != NGX_OK) {
        ngx_log_error(NGX_LOG_ERR, r->connection->log, 0,
                      "wormhole: failed to parse daemon URL: %V", &conf->daemon_url);
        return NGX_HTTP_INTERNAL_SERVER_ERROR;
    }

    /* Set X-Wormhole-Original-Host header for daemon */
    ngx_table_elt_t *hdr = ngx_list_push(&r->headers_in.headers);
    if (hdr == NULL) {
        return NGX_HTTP_INTERNAL_SERVER_ERROR;
    }

    hdr->hash = 1;
    ngx_str_set(&hdr->key, "X-Wormhole-Original-Host");
    hdr->value = r->headers_in.host->value;
    hdr->lowcase_key = (u_char *)"x-wormhole-original-host";

    /* Set X-Wormhole-Identity header */
    if (conf->identity.len > 0) {
        hdr = ngx_list_push(&r->headers_in.headers);
        if (hdr == NULL) {
            return NGX_HTTP_INTERNAL_SERVER_ERROR;
        }

        hdr->hash = 1;
        ngx_str_set(&hdr->key, "X-Wormhole-Identity");
        hdr->value = conf->identity;
        hdr->lowcase_key = (u_char *)"x-wormhole-identity";
    }

    /* Build internal redirect location */
    len = conf->daemon_url.len + proxy_uri.len;
    daemon_host.data = ngx_pnalloc(r->pool, len);
    if (daemon_host.data == NULL) {
        return NGX_HTTP_INTERNAL_SERVER_ERROR;
    }

    p = ngx_cpymem(daemon_host.data, conf->daemon_url.data, conf->daemon_url.len);
    p = ngx_cpymem(p, proxy_uri.data, proxy_uri.len);
    daemon_host.len = len;

    ngx_log_error(NGX_LOG_INFO, r->connection->log, 0,
                  "wormhole: proxying %V to daemon: %V",
                  wns_name, &daemon_host);

    /* Use internal redirect to proxy to daemon */
    r->uri = proxy_uri;
    r->uri_changed = 1;

    /* Update the Host header to point to daemon */
    if (u.host.len > 0) {
        r->headers_in.host->value.data = u.host.data;
        r->headers_in.host->value.len = u.host.len;
    }

    /*
     * Note: For full proxy functionality, this module should be combined
     * with nginx's proxy_pass directive. The internal redirect will route
     * to a location block configured with proxy_pass to the daemon.
     *
     * Example nginx.conf:
     *   location @wormhole_proxy {
     *       internal;
     *       proxy_pass http://localhost:8080;
     *   }
     *
     * For now, we use NGX_DECLINED to pass to the next handler,
     * which allows nginx's standard proxy module to handle the request.
     */

    return NGX_DECLINED;
}

/*
 * Main request handler
 *
 * This handler intercepts incoming requests and checks if they are
 * wormhole requests. If so, it proxies them to the wormhole daemon.
 *
 * Flow:
 * 1. Check if wormhole is enabled
 * 2. Check if this is a wormhole request (wh:// or .wns)
 * 3. Extract the WNS name
 * 4. Proxy to daemon's /browse endpoint
 * 5. Daemon handles DHT resolution and connection
 */
static ngx_int_t
ngx_http_wormhole_handler(ngx_http_request_t *r)
{
    ngx_http_wormhole_loc_conf_t  *conf;
    ngx_str_t                      wns_name;
    ngx_int_t                      rc;

    conf = ngx_http_get_module_loc_conf(r, ngx_http_wormhole_module);

    /* Check if module is enabled */
    if (!conf->enable) {
        return NGX_DECLINED;
    }

    /* Log handler invocation */
    ngx_log_error(NGX_LOG_DEBUG, r->connection->log, 0,
                  "wormhole: handler called for URI: %V, Host: %V",
                  &r->uri,
                  r->headers_in.host ? &r->headers_in.host->value : &(ngx_str_t)ngx_string("(none)"));

    /* Check if this is a wormhole request */
    ngx_memzero(&wns_name, sizeof(ngx_str_t));
    if (!is_wormhole_request(r, &wns_name)) {
        ngx_log_error(NGX_LOG_DEBUG, r->connection->log, 0,
                      "wormhole: not a wormhole request, declining");
        return NGX_DECLINED;
    }

    /* Validate WNS name */
    if (wns_name.len == 0) {
        ngx_log_error(NGX_LOG_ERR, r->connection->log, 0,
                      "wormhole: empty WNS name");
        return NGX_HTTP_BAD_REQUEST;
    }

    if (wns_name.len > 253) {  /* Max DNS name length */
        ngx_log_error(NGX_LOG_ERR, r->connection->log, 0,
                      "wormhole: WNS name too long: %uz bytes", wns_name.len);
        return NGX_HTTP_BAD_REQUEST;
    }

    ngx_log_error(NGX_LOG_INFO, r->connection->log, 0,
                  "wormhole: processing request for WNS name: %V", &wns_name);

    /* Proxy to daemon */
    rc = ngx_http_wormhole_proxy_to_daemon(r, conf, &wns_name);
    if (rc != NGX_DECLINED && rc != NGX_OK) {
        ngx_log_error(NGX_LOG_ERR, r->connection->log, 0,
                      "wormhole: failed to proxy request, rc=%d", rc);
        return rc;
    }

    return rc;
}

/*
 * Module initialization
 */
static ngx_int_t
ngx_http_wormhole_init(ngx_conf_t *cf)
{
    ngx_http_handler_pt        *h;
    ngx_http_core_main_conf_t  *cmcf;

    cmcf = ngx_http_conf_get_module_main_conf(cf, ngx_http_core_module);

    h = ngx_array_push(&cmcf->phases[NGX_HTTP_REWRITE_PHASE].handlers);
    if (h == NULL) {
        return NGX_ERROR;
    }

    *h = ngx_http_wormhole_handler;

    return NGX_OK;
}
