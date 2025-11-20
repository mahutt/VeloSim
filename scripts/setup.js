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

    // Step 7: Prepare OSRM data
    console.log('\n[SETUP] Preparing OSRM routing data...');
    console.log('[INFO] This will download Montreal map data (~50-100MB)');
    console.log('[INFO] This is a one-time setup and may take 3-5 minutes');
    try {
      await runCommand('node', ['scripts/prepare-osrm.js']);
    } catch (error) {
      console.log('[WARNING] OSRM data preparation failed');
      console.log('[INFO] You can run this manually later: npm run osrm:prepare');
      console.log('[INFO] Error:', error.message);
    }

    console.log('\n[SUCCESS] Setup completed successfully!');

  } catch (error) {
    console.error(`\n[ERROR] Setup failed: ${error.message}`);
    process.exit(1);
  }
}

main();
