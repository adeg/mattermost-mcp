job "mattermost-mcp" {
  datacenters = ["dc1"]
  type        = "service"

  meta {
    version = "1.0.0"
  }

  group "mcp" {
    count = 1

    network {
      port "http" {
        to = 8000
      }
    }

    service {
      name = "mattermost-mcp"
      port = "http"

      check {
        type     = "http"
        path     = "/health"
        interval = "30s"
        timeout  = "5s"
      }

      check {
        type     = "http"
        path     = "/ready"
        interval = "60s"
        timeout  = "10s"
      }

      tags = [
        "traefik.enable=true",
        "traefik.http.routers.mattermost-mcp.rule=Host(`mcp.example.com`)",
        "traefik.http.routers.mattermost-mcp.entrypoints=websecure",
        "traefik.http.routers.mattermost-mcp.tls=true",
      ]
    }

    restart {
      attempts = 3
      interval = "5m"
      delay    = "15s"
      mode     = "fail"
    }

    task "server" {
      driver = "docker"

      config {
        image = "registry.example.com/mattermost-mcp:latest"
        ports = ["http"]

        volumes = [
          "local/data:/data/mattermost-mcp",
        ]
      }

      env {
        HTTP_PORT  = "${NOMAD_PORT_http}"
        LOG_FORMAT = "json"
        LOG_LEVEL  = "INFO"
      }

      template {
        destination = "secrets/env.txt"
        env         = true
        data        = <<EOF
{{ with secret "secret/data/mattermost-mcp" }}
MATTERMOST_URL={{ .Data.data.mattermost_url }}
MATTERMOST_TOKEN={{ .Data.data.mattermost_token }}
MATTERMOST_TEAM_ID={{ .Data.data.team_id }}
{{ if .Data.data.anthropic_api_key }}
ANTHROPIC_API_KEY={{ .Data.data.anthropic_api_key }}
{{ end }}
{{ if .Data.data.monitoring_enabled }}
MONITORING_ENABLED={{ .Data.data.monitoring_enabled }}
MONITORING_CHANNELS={{ .Data.data.monitoring_channels }}
MONITORING_TOPICS={{ .Data.data.monitoring_topics }}
MONITORING_SCHEDULE={{ .Data.data.monitoring_schedule | default "*/5 * * * *" }}
{{ end }}
{{ end }}
EOF
      }

      resources {
        cpu    = 256
        memory = 512
      }

      volume_mount {
        volume      = "data"
        destination = "/data/mattermost-mcp"
        read_only   = false
      }

      logs {
        max_files     = 5
        max_file_size = 10
      }
    }

    volume "data" {
      type      = "host"
      source    = "mattermost-mcp-data"
      read_only = false
    }
  }
}
