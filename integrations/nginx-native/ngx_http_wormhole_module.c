/*
 * ngx_http_wormhole_module.c - Native Nginx module for Wormhole Name System
 *
 * This module integrates WNS resolution directly into Nginx by communicating
 * with the wh daemon API.
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

/* Forward declarations */
static ngx_int_t ngx_http_wormhole_handler(ngx_http_request_t *r);
static void *ngx_http_wormhole_create_loc_conf(ngx_conf_t *cf);
static char *ngx_http_wormhole_merge_loc_conf(ngx_conf_t *cf, void *parent, void *child);
static ngx_int_t ngx_http_wormhole_init(ngx_conf_t *cf);

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
 * Main request handler
 *
 * TODO: Implement actual wormhole resolution and proxying logic:
 * 1. Check if request is for wh:// URL
 * 2. Query daemon API for DHT resolution
 * 3. Establish connection to peer
 * 4. Proxy request/response
 * 5. Cache connection for reuse
 */
static ngx_int_t
ngx_http_wormhole_handler(ngx_http_request_t *r)
{
    ngx_http_wormhole_loc_conf_t *conf;

    conf = ngx_http_get_module_loc_conf(r, ngx_http_wormhole_module);

    if (!conf->enable) {
        return NGX_DECLINED;
    }

    /* TODO: Implement handler logic */
    ngx_log_error(NGX_LOG_DEBUG, r->connection->log, 0,
                  "wormhole: handler called for URI: %V", &r->uri);

    /*
     * Handler stub:
     * 1. Parse Host header for wh:// scheme
     * 2. Call daemon API: POST /resolve with {name: "example.tld"}
     * 3. Get peer connection info from response
     * 4. Establish connection using wormhole protocol
     * 5. Forward HTTP request to peer
     * 6. Stream response back to client
     */

    return NGX_DECLINED;
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
