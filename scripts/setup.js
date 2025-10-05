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
 * Ensures proper installation of dependencies in virtual environment
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
      shell: true,
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
    // Step 0: Detect which Python interpreter run-python.js will use
    console.log('[CHECK] Detecting Python environment...');
    let detectedPython = null;
    let actualPythonPath = null;

    try {
      const versionResult = await runCommandWithOutput('node', ['scripts/run-python.js', '--version']);
      console.log(`[INFO] ${versionResult.stdout}`);

      try {
        const pathResult = await runCommandWithOutput('node', ['scripts/run-python.js', '-c', 'import sys; print(sys.executable)']);
        detectedPython = pathResult.stdout.trim();
        actualPythonPath = detectedPython;
        console.log(`[INFO] Python executable: ${detectedPython}`);
      } catch (pathError) {
        console.log('[INFO] Could not determine exact Python path via run-python.js, using fallback detection...');
        detectedPython = 'python';

        // Try to get the actual Python path that 'python' command resolves to
        try {
          const fallbackResult = await runCommandWithOutput('python', ['-c', 'import sys; print(sys.executable)']);
          actualPythonPath = fallbackResult.stdout.trim();
          console.log(`[INFO] Fallback Python executable: ${actualPythonPath}`);
        } catch (fallbackError) {
          console.log('[INFO] Could not determine Python executable path');
          actualPythonPath = 'python (path unknown)';
        }
      }
    } catch (error) {
      console.log('[WARNING] Could not detect Python environment details, falling back to system python...');
      detectedPython = 'python';
      actualPythonPath = 'python (unknown)';
    }

    // Use the detected Python for all subsequent operations
    const pythonExe = detectedPython;
    console.log(`[SUCCESS] Using Python command: ${pythonExe}`);
    if (actualPythonPath && actualPythonPath !== detectedPython) {
      console.log(`[INFO] Actual Python executable: ${actualPythonPath}`);
    }

    const venvPath = path.join(process.cwd(), '.venv');

    // Step 1: Create .venv if it doesn't exist (but don't force its use)
    if (!fs.existsSync(venvPath)) {
      console.log('\n[SETUP] Creating .venv virtual environment for future use...');
      await runCommand(pythonExe, ['-m', 'venv', '.venv']);
      console.log('[INFO] .venv created but current Python environment will be used for setup');
    } else {
      console.log('\n[INFO] .venv already exists');
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

    // Step 5: Install frontend dependencies
    console.log('\n[INSTALL] Installing frontend dependencies...');
    await runCommand('npm', ['install'], { cwd: path.join(process.cwd(), 'front') });

    console.log('\n[SUCCESS] Setup completed successfully!');

  } catch (error) {
    console.error(`\n[ERROR] Setup failed: ${error.message}`);
    process.exit(1);
  }
}

main();
