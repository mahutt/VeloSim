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
 * Wait for Docker container health check
 * Usage: node scripts/wait-for-health.js <container-name> [timeout-seconds]
 */

const { execSync } = require('child_process');

const containerName = process.argv[2];
const timeoutSeconds = parseInt(process.argv[3] || '60', 10);

if (!containerName) {
    console.error('Error: Please provide a container name');
    console.error('Usage: node scripts/wait-for-health.js <container-name> [timeout-seconds]');
    process.exit(1);
}

function getContainerHealth(name) {
    try {
        const result = execSync(
            `docker inspect --format='{{.State.Health.Status}}' ${name}`,
            { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'ignore'] }
        );
        return result.trim();
    } catch (error) {
        // Container doesn't exist or doesn't have health check
        return null;
    }
}

function isContainerRunning(name) {
    try {
        const result = execSync(
            `docker inspect --format='{{.State.Status}}' ${name}`,
            { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'ignore'] }
        );
        return result.trim() === 'running';
    } catch (error) {
        return false;
    }
}

async function waitForHealth() {
    console.log(`Waiting for ${containerName} to be healthy...`);

    const startTime = Date.now();
    const maxTime = timeoutSeconds * 1000;

    while (Date.now() - startTime < maxTime) {
        if (!isContainerRunning(containerName)) {
            // Container not running - just wait a bit, it might be starting
            await new Promise(resolve => setTimeout(resolve, 500));
            continue;
        }

        const health = getContainerHealth(containerName);

        if (health === 'healthy') {
            console.log(`${containerName} is healthy! ✓`);
            return;
        } else if (health === null) {
            // No health check defined, just verify it's running
            console.log(`${containerName} is running (no health check defined) ✓`);
            return;
        }

        // Still starting, wait a bit
        await new Promise(resolve => setTimeout(resolve, 500));
    }

    // Timeout reached - but don't fail, just warn
    console.warn(`Warning: Timeout waiting for ${containerName} to be healthy, but continuing anyway...`);
}

waitForHealth().catch(error => {
    console.error('Error:', error.message);
    process.exit(1);
});
