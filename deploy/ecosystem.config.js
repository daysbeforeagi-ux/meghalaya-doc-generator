// PM2 process config for the Orator Next.js frontend.
// Usage:
//   pm2 start deploy/ecosystem.config.js
//   pm2 save && pm2 startup   (persist across reboots)

module.exports = {
  apps: [
    {
      name: "orator-web",
      cwd: "/opt/orator/web",
      script: "node_modules/.bin/next",
      args: "start --port 3000",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "512M",
      env: {
        NODE_ENV: "production",
        PORT: 3000,
      },
      error_file: "/var/log/orator/web-error.log",
      out_file: "/var/log/orator/web-out.log",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
    },
  ],
};
