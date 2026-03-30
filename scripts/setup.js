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
 */

/**
 * VeloSim Setup Script
 *
 * This script installs Python dependencies in your LOCAL environment for:
 * - IDE autocomplete and IntelliSense
 * - Running linters and formatters (black, flake8, mypy)
 * - Running tests locally without Docker
 *
 * Note: If you're using the containerized development workflow (docker-compose),
 * dependencies are automatically installed inside containers. This local setup
 * is optional but recommended for better IDE support.
 *
 * For containerized development:
 * - Use: npm run dev (runs backend/frontend in containers)
 * - Dependencies are managed in Dockerfile and installed during build
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const readline = require('readline');
const crypto = require('crypto');

const isWindows = process.platform === 'win32';

function runCommand(cmd, args = [], options = {}) {
  return new Promise((resolve, reject) => {
    console.log(`Running: ${cmd} ${args.join(' ')}`);

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

function runCommandWithOutput(cmd, args = [], options = {}) {
  return new Promise((resolve, reject) => {
    let stdout = '';
    let stderr = '';

    const child = spawn(cmd, args, {
      stdio: 'pipe',
      shell: false,  // Don't use shell for simple commands to avoid security warnings
      cwd: options.cwd || process.cwd(),
      ...options
    });

    child.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    child.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    child.on('close', (code) => {
      if (code === 0) {
        resolve({ stdout: stdout.trim(), stderr: stderr.trim() });
      } else {
        reject(new Error(`Command failed with exit code ${code}. stderr: ${stderr}`));
      }
    });

    child.on('error', (err) => {
      reject(err);
    });
  });
}

function promptUser(question) {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      rl.close();
      // Remove all whitespace including newlines
      resolve(answer.replace(/\s+/g, '').trim());
    });
  });
}

function generateJWTSecret() {
  return crypto.randomBytes(32).toString('hex');
}

async function setupEnvFile() {
  const envPath = path.join(process.cwd(), '.env');

  // Check if .env already exists
  if (fs.existsSync(envPath)) {
    console.log('\n[INFO] .env file already exists. Skipping environment setup.');
    console.log('[INFO] To reconfigure, delete .env and run setup again.');
    return;
  }

  console.log('\n[SETUP] Environment Configuration');
  console.log('='.repeat(50));
  console.log('Setting up your .env file for local development.\n');

  // Prompt for Mapbox token
  console.log('[OPTIONAL] Mapbox Access Token');
  console.log('Required for map visualization. Get a free token at:');
  console.log('https://account.mapbox.com/access-tokens/\n');

  const mapboxToken = await promptUser('Enter Mapbox token (or press Enter to skip): ');

  if (!mapboxToken) {
    console.log('[WARNING] Maps will not work without a Mapbox token.');
    console.log('[INFO] You can add it later by editing .env\n');
  }

  // Generate JWT secret
  const jwtSecret = generateJWTSecret();
  console.log('[GENERATED] Random JWT secret for authentication\n');

  // Create .env content
  const envContent = `# VeloSim Environment Configuration
# Auto-generated by npm run setup on ${new Date().toISOString()}

# ============================================================================
# GraphHopper Routing Server (REQUIRED)
# ============================================================================
GRAPHHOPPER_URL=http://localhost:8989

# ============================================================================
# Database (REQUIRED)
# ============================================================================
DATABASE_URL=postgresql://velosim:velosim@localhost:5433/velosim

# ============================================================================
# Frontend
# ============================================================================
# Backend API URL for frontend (defaults to http://localhost:8000 if not set)
BACKEND_URL=http://localhost:8000

# Mapbox access token for map rendering
${mapboxToken ? `MAPBOX_ACCESS_TOKEN=${mapboxToken}` : '# MAPBOX_ACCESS_TOKEN=your-token-here'}

# ============================================================================
# Security
# ============================================================================
# JWT secret for authentication (auto-generated)
VELOSIM_JWT_SECRET=${jwtSecret}

# ============================================================================
# Logging (OPTIONAL)
# ============================================================================
# Disable Loki log push for local development (Loki is not started by dev:services)
# On Windows, leaving this enabled causes the backend to hang on every request
# because DNS resolution for the Docker-internal hostname blocks the event loop.
LOG_TO_LOKI=false
`;

  // Write .env file
  fs.writeFileSync(envPath, envContent, 'utf-8');
  console.log('[SUCCESS] Created .env file with your configuration');
}

async function main() {
  console.log('Setting up VeloSim development environment...\n');

  try {
    // Step 0: Detect or select Python environment
    console.log('[CHECK] Detecting Python environment...');
    let pythonExe = null;
    let actualPythonPath = null;
    let isVirtualEnv = false;

    // Priority 1: Respect active virtual environment (VIRTUAL_ENV)
    if (process.env.VIRTUAL_ENV) {
      const venvPython = isWindows
        ? `"${path.join(process.env.VIRTUAL_ENV, 'Scripts', 'python.exe')}"`
        : path.join(process.env.VIRTUAL_ENV, 'bin', 'python');

      if (fs.existsSync(venvPython)) {
        pythonExe = venvPython;
        actualPythonPath = venvPython;
        isVirtualEnv = true;
        console.log(`[INFO] Using active virtual environment: ${process.env.VIRTUAL_ENV}`);
        console.log(`[INFO] Python executable: ${pythonExe}`);
      }
    }

    // Priority 2: Check for local .venv directory
    if (!pythonExe) {
      const venvPath = path.join(process.cwd(), '.venv');
      const venvPython = isWindows
        ? `"${path.join(venvPath, 'Scripts', 'python.exe')}"`
        : path.join(venvPath, 'bin', 'python');

      if (fs.existsSync(venvPython)) {
        pythonExe = venvPython;
        actualPythonPath = venvPython;
        isVirtualEnv = true;
        console.log(`[INFO] Using local .venv: ${venvPath}`);
        console.log(`[INFO] Python executable: ${pythonExe}`);
      }
    }

    // Priority 3: Fall back to system Python
    if (!pythonExe) {
      // Try different Python commands based on platform
      // Windows: python, py -3, python3
      // macOS/Linux: python3, python
      const pythonCommands = isWindows
        ? ['python', 'py', 'python3']
        : ['python3', 'python'];

      let foundPython = false;

      for (const cmd of pythonCommands) {
        try {
          const result = await runCommandWithOutput(cmd, ['-c', 'import sys; print(sys.executable)']);
          pythonExe = cmd;
          actualPythonPath = result.stdout.trim();
          foundPython = true;
          console.log(`[INFO] No virtual environment detected, using system Python: ${cmd}`);
          console.log(`[INFO] Python executable: ${actualPythonPath}`);
          break;
        } catch (error) {
          // Try next command
          continue;
        }
      }

      if (!foundPython) {
        const installMsg = isWindows
          ? 'Please install Python 3.11+ from https://www.python.org/downloads/ or Microsoft Store'
          : 'Please install Python 3.11+ using your package manager (brew install python3, apt install python3, etc.)';
        throw new Error(`Python not found. ${installMsg}`);
      }
    }

    // Display Python version
    try {
      const versionResult = await runCommandWithOutput(pythonExe, ['--version']);
      console.log(`[INFO] ${versionResult.stdout}`);
    } catch (error) {
      console.log('[WARNING] Could not determine Python version');
    }

    const venvPath = path.join(process.cwd(), '.venv');

    // Step 1: Create .venv if no virtual environment is active
    if (!isVirtualEnv && !fs.existsSync(venvPath)) {
      console.log('\n[SETUP] No virtual environment detected. Creating .venv...');
      console.log('[INFO] You can also use your own virtual environment (pyenv, venv, etc.) and activate it before running setup');

      // Use the detected pythonExe (python3 or python) to create venv
      await runCommand(pythonExe, ['-m', 'venv', '.venv']);

      // Update pythonExe to use the newly created .venv
      pythonExe = isWindows
        ? `"${path.join(venvPath, 'Scripts', 'python.exe')}"`
        : path.join(venvPath, 'bin', 'python');

      actualPythonPath = pythonExe;
      isVirtualEnv = true;
      console.log(`[SUCCESS] Created .venv and will use it for installation`);
      console.log(`[INFO] Python executable: ${pythonExe}`);
    } else if (!isVirtualEnv && fs.existsSync(venvPath)) {
      console.log('\n[INFO] .venv exists. Using it for installation...');
      // Update pythonExe to use the existing .venv
      pythonExe = isWindows
        ? `"${path.join(venvPath, 'Scripts', 'python.exe')}"`
        : path.join(venvPath, 'bin', 'python');
      actualPythonPath = pythonExe;
      isVirtualEnv = true;
      console.log(`[INFO] Python executable: ${pythonExe}`);
    } else {
      console.log('\n[INFO] Using active virtual environment for installation');
    }

    // Step 2: Check if pip works with the detected Python
    console.log('\n[CHECK] Checking pip installation...');
    try {
      await runCommand(pythonExe, ['-m', 'pip', '--version']);
    } catch (error) {
      console.log('[ERROR] Pip is not working with the detected Python interpreter');
      throw new Error('Pip is not available in the current Python environment');
    }

    // Step 3: Install Python dependencies using the detected Python
    console.log('\n[INSTALL] Installing Python dependencies...');
    await runCommand(pythonExe, ['-m', 'pip', 'install', '-e', '.[dev]']);

    // Step 4: Install pre-commit hooks using the detected Python
    console.log('\n[SETUP] Installing pre-commit hooks...');
    await runCommand(pythonExe, ['-m', 'pre_commit', 'install']);

    // Step 5: Install root npm dependencies (concurrently, rimraf, etc.)
    console.log('\n[INSTALL] Installing root npm dependencies...');
    await runCommand('npm', ['install']);

    // Step 6: Install frontend dependencies
    console.log('\n[INSTALL] Installing frontend dependencies...');
    await runCommand('npm', ['install'], { cwd: path.join(process.cwd(), 'front') });

    // Step 7: Setup environment file
    await setupEnvFile();

    // Step 8: Prepare GraphHopper data
    console.log('\n[SETUP] Preparing GraphHopper routing data...');
    console.log('[INFO] This will download Montreal map data (~50-100MB)');
    console.log('[INFO] This is a one-time setup and may take 3-5 minutes');
    try {
      await runCommand('node', ['scripts/prepare-graphhopper.js']);
    } catch (error) {
      console.log('[WARNING] GraphHopper data preparation failed');
      console.log('[INFO] You can run this manually later: npm run graphhopper:prepare');
      console.log('[INFO] Error:', error.message);
    }

    // Step 9: Initialize database
    console.log('\n[SETUP] Initializing database...');
    console.log('[INFO] Starting Docker services (postgres, GraphHopper)...');
    try {
      await runCommand('npm', ['run', 'dev:services']);
      console.log('[INFO] Running database migrations and seeds...');
      await runCommand('npm', ['run', 'db:upgrade']);
      await runCommand('npm', ['run', 'db:seed']);
      console.log('[SUCCESS] Database initialized with seed data');
    } catch (error) {
      console.log('[WARNING] Database setup failed');
      console.log('[INFO] You can run migrations manually: npm run db:upgrade && npm run db:seed');
      console.log('[INFO] Error:', error.message);
    }

    // Step 10: Prepare Traffic Datasets
    console.log('\n[SETUP] Preparing traffic datasets...');
    console.log('[INFO] This will download the Montreal dataset and create the traffic csv');
    console.log('[INFO] This is a one-time setup and may take about 3-5 minutes')
    try {
      await runCommand('npm', ['run', 'traffic-csv']);
      console.log('[SUCCESS] Traffic datasets ready for use');
    } catch (error) {
      console.log('[WARNING] Traffic csv setup failed');
      console.log('[INFO] You can run manually the script: npm run traffic-csv')
      console.log('[INFO] Error:', error.message);
    }

    // Step 11: Get Traffic Templates
    console.log('\n[SETUP] Retrieving traffic templates...');
    try {
      await runCommand('npm', ['run', 'traffic-templates']);
       console.log('[SUCCESS] Retrieved all three traffic templates')
    } catch (error) {
      console.log('[WARNING] Traffic template retrieval failed')
      console.log('[INFO] You can run manually the script: npm run traffic-templates')
      console.log('[INFO] Error:', error.message);
    }

    console.log('\n[SUCCESS] Setup completed successfully!');
    console.log('\nNext step:');
    console.log('  npm run dev  # Start development servers');

  } catch (error) {
    console.error(`\n[ERROR] Setup failed: ${error.message}`);
    process.exit(1);
  }
}

main();
