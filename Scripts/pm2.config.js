// pm2.config.js — AI Employee Vault process manager configuration
//
// Manages all watcher scripts and the orchestrator as persistent PM2 apps.
//
// Usage:
//   npm install -g pm2                    # install PM2 once
//   pm2 start pm2.config.js              # start all (DRY_RUN=true, safe)
//   pm2 start pm2.config.js --env prod   # start all (DRY_RUN=false, live)
//   pm2 save                             # save process list
//   pm2 startup                          # generate auto-start on boot
//   pm2 logs                             # tail all logs
//   pm2 status                           # show process table
//   pm2 stop all                         # stop all
//   pm2 restart all                      # restart all
//
// Requirements:
//   - PM2 installed globally: npm install -g pm2
//   - UV on PATH: uv --version must work from a terminal
//   - .env file configured at vault root (copy from .env.example)
//   - Run 'Scripts/gmail_auth.py' and 'Scripts/linkedin_auth.py' first
//
// Note on DRY_RUN:
//   The default env keeps DRY_RUN=true (no external actions).
//   Use --env prod to flip to DRY_RUN=false only after testing.

const VAULT = "G:/Hackathons/GIAIC_Hackathons/AI_Employee_Vault";

// Use pythonw.exe (the windowless Python variant) so PM2-spawned processes
// never create a console window — no PM2 config tricks required.
// Python automatically adds the script's directory (Scripts/) to sys.path,
// so cross-script imports (e.g. from base_watcher import BaseWatcher) work.
const PYTHONW = `${VAULT}/.venv/Scripts/pythonw.exe`;

function cmd(script) {
  return {
    script: PYTHONW,
    args: `Scripts/${script}`,
    interpreter: "none",
  };
}

/** @type {import('pm2').StartOptions[]} */
module.exports = {
  apps: [
    // -----------------------------------------------------------------------
    // Gmail Watcher — polls Gmail for unread important emails
    // -----------------------------------------------------------------------
    {
      name: "gmail-watcher",
      ...cmd("gmail_watcher.py"),
      cwd: VAULT,
      env: {
        DRY_RUN: "true",
      },
      env_production: {
        DRY_RUN: "false",
      },
      restart_delay: 5000,
      max_restarts: 10,
      watch: false,
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      error_file: `${VAULT}/Logs/pm2-gmail-error.log`,
      out_file: `${VAULT}/Logs/pm2-gmail-out.log`,
    },

    // -----------------------------------------------------------------------
    // WhatsApp Watcher — scrapes WhatsApp Web via Playwright
    // -----------------------------------------------------------------------
    {
      name: "whatsapp-watcher",
      ...cmd("whatsapp_watcher.py"),
      cwd: VAULT,
      env: {
        DRY_RUN: "true",
      },
      env_production: {
        DRY_RUN: "false",
      },
      // Playwright needs extra restart delay to reopen the browser cleanly
      restart_delay: 15000,
      max_restarts: 5,
      watch: false,
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      error_file: `${VAULT}/Logs/pm2-whatsapp-error.log`,
      out_file: `${VAULT}/Logs/pm2-whatsapp-out.log`,
    },

    // -----------------------------------------------------------------------
    // Discord Watcher — discord.py bot listening on guild events
    // -----------------------------------------------------------------------
    {
      name: "discord-watcher",
      ...cmd("discord_watcher.py"),
      cwd: VAULT,
      env: {
        DRY_RUN: "true",
      },
      env_production: {
        DRY_RUN: "false",
      },
      restart_delay: 5000,
      max_restarts: 10,
      watch: false,
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      error_file: `${VAULT}/Logs/pm2-discord-error.log`,
      out_file: `${VAULT}/Logs/pm2-discord-out.log`,
    },

    // -----------------------------------------------------------------------
    // LinkedIn Watcher — scrapes LinkedIn messages via Playwright
    // -----------------------------------------------------------------------
    {
      name: "linkedin-watcher",
      ...cmd("linkedin_watcher.py"),
      cwd: VAULT,
      env: {
        DRY_RUN: "true",
      },
      env_production: {
        DRY_RUN: "false",
      },
      restart_delay: 15000,
      max_restarts: 5,
      watch: false,
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      error_file: `${VAULT}/Logs/pm2-linkedin-error.log`,
      out_file: `${VAULT}/Logs/pm2-linkedin-out.log`,
    },

    // -----------------------------------------------------------------------
    // Orchestrator — dispatches approved actions from Approved/
    // -----------------------------------------------------------------------
    {
      name: "orchestrator",
      ...cmd("orchestrator.py"),
      cwd: VAULT,
      env: {
        DRY_RUN: "true",
      },
      env_production: {
        DRY_RUN: "false",
      },
      restart_delay: 5000,
      max_restarts: 10,
      watch: false,
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      error_file: `${VAULT}/Logs/pm2-orchestrator-error.log`,
      out_file: `${VAULT}/Logs/pm2-orchestrator-out.log`,
    },
  ],
};
