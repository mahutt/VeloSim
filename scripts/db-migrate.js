#!/usr/bin/env node

/**
 * MIT License
 *
 * Copyright (c) 2025 VeloSim Contributors
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *//**
 * Cross-platform database migration script for VeloSim
 * Supports both Windows and Unix-like systems (macOS, Linux)
 * Uses direct Alembic commands for migrations
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Detect operating system
const isWindows = process.platform === 'win32';

// Get command line arguments
const [,, command, ...args] = process.argv;

// Define available commands
const commands = {
  'current': 'Check current migration status',
  'generate': 'Generate new migration (requires message)',
  'upgrade': 'Apply pending migrations',
  'downgrade': 'Rollback last migration',
  'history': 'Show migration history',
  'seed': 'Seed database with initial station data',
  'dropseed': 'Drop database, run migrations, and seed data (fixes enum issues)',
  'status': 'Alias for current'
};

function showHelp() {
  console.log('INFO  [velosim.db_migrate] VeloSim Database Migration Tool\n');
  console.log('Usage: npm run db:<command> [arguments]\n');
  console.log('Available commands:');
  Object.entries(commands).forEach(([cmd, desc]) => {
    console.log(`  ${cmd.padEnd(12)} - ${desc}`);
  });
  console.log('\nExamples:');
  console.log('  npm run db:current');
  console.log('  npm run db:generate "Add stations table"');
  console.log('  npm run db:upgrade');
  console.log('  npm run db:seed');
  console.log('  npm run db:dropseed');
  console.log('\nNote: Uses .env DATABASE_URL configuration for database connections');
}

function runCommand(cmd, args = [], options = {}) {
  return new Promise((resolve, reject) => {
    console.log(`INFO  [velosim.db_migrate] Running: ${cmd} ${args.join(' ')}`);

    const child = spawn(cmd, args, {
      stdio: 'inherit',
      shell: true,
      cwd: options.cwd || process.cwd(),
      ...options
    });

    child.on('close', (code) => {
      if (code === 0) {
        resolve(code);
      } else {
        reject(new Error(`Command failed with exit code ${code}`));
      }
    });

    child.on('error', (err) => {
      reject(err);
    });
  });
}

async function main() {
  // Show help if no command or help requested
  if (!command || command === 'help' || command === '--help' || command === '-h') {
    showHelp();
    return;
  }

  // Validate command
  if (!commands[command] && command !== 'downgrade' && command !== 'dropseed') {
    console.error(`ERROR [velosim.db_migrate] Unknown command: ${command}`);
    showHelp();
    process.exit(1);
  }

  // Check if we're in the root directory
  const packageJsonPath = path.join(process.cwd(), 'package.json');
  if (!fs.existsSync(packageJsonPath)) {
    console.error('ERROR [velosim.db_migrate] This script must be run from the project root directory');
    process.exit(1);
  }

  // Change to back directory for migration commands
  const backDir = path.join(process.cwd(), 'back');
  if (!fs.existsSync(backDir)) {
    console.error('ERROR [velosim.db_migrate] Back directory not found. Make sure you\'re in the VeloSim root directory.');
    process.exit(1);
  }

  try {
    let cmd, cmdArgs;

    if (isWindows) {
      // Use batch file on Windows
      const batchScript = path.join(process.cwd(), 'scripts', 'migrate.bat');
      if (!fs.existsSync(batchScript)) {
        console.error('ERROR [velosim.db_migrate] migrate.bat not found in scripts directory');
        process.exit(1);
      }
      cmd = 'cmd.exe';
      cmdArgs = ['/c', `"${batchScript}"`, command, ...args];
    } else {
      // Use shell script on Unix-like systems
      const shellScript = path.join(process.cwd(), 'scripts', 'migrate.sh');
      if (!fs.existsSync(shellScript)) {
        console.error('ERROR [velosim.db_migrate] migrate.sh not found in scripts directory');
        process.exit(1);
      }
      cmd = 'bash';
      cmdArgs = [shellScript, command, ...args];
    }

    // Special handling for generate command that needs a message
    if (command === 'generate') {
      if (args.length === 0) {
        console.error('ERROR [velosim.db_migrate] Generate command requires a migration message');
        console.log('Example: npm run db:generate "Add stations table"');
        process.exit(1);
      }
    }

    console.log(`INFO  [velosim.db_migrate] Running migration command: ${command}`);
    console.log(`INFO  [velosim.db_migrate] Using scripts from: scripts/`);
    console.log(`INFO  [velosim.db_migrate] Platform: ${isWindows ? 'Windows (using migrate.bat)' : 'Unix-like (using migrate.sh)'}\n`);

    await runCommand(cmd, cmdArgs, { cwd: process.cwd() });
    console.log(`\nINFO  [velosim.db_migrate] Migration command completed successfully!`);

  } catch (error) {
    console.error(`\nERROR [velosim.db_migrate] Migration command failed: ${error.message}`);
    process.exit(1);
  }
}

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  console.error('ERROR [velosim.db_migrate] Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

// Run the main function
main().catch((error) => {
  console.error('ERROR [velosim.db_migrate] Fatal error:', error);
  process.exit(1);
});
