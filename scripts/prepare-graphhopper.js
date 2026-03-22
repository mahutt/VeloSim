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

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const https = require('https');

const ROOT = path.join(__dirname, '..');
const GH_DIR = path.join(ROOT, 'graphhopper-data');
const OSM_FILE = path.join(GH_DIR, 'montreal-latest.osm.pbf');
const DOWNLOAD_URL = 'https://download.bbbike.org/osm/bbbike/Montreal/Montreal.osm.pbf';
const FORCE = process.argv.includes('--force');

function download(url, outFile) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(outFile);
    https.get(url, (response) => {
      if (response.statusCode === 301 || response.statusCode === 302) {
        file.close();
        fs.unlinkSync(outFile);
        return download(response.headers.location, outFile).then(resolve).catch(reject);
      }
      if (response.statusCode !== 200) {
        file.close();
        fs.unlinkSync(outFile);
        return reject(new Error(`Download failed with HTTP ${response.statusCode}`));
      }
      response.pipe(file);
      file.on('finish', () => file.close(resolve));
    }).on('error', (err) => {
      file.close();
      if (fs.existsSync(outFile)) fs.unlinkSync(outFile);
      reject(err);
    });
  });
}

async function main() {
  console.log('VeloSim GraphHopper Data Preparation\n');

  // Clear cache FIRST in force mode
  if (FORCE && fs.existsSync(GH_DIR)) {
    console.log('Clearing existing graphhopper-data cache...');
    fs.rmSync(GH_DIR, { recursive: true, force: true });
  }

  // Ensure directory exists
  fs.mkdirSync(GH_DIR, { recursive: true });

  // Download OSM file if missing
  if (!fs.existsSync(OSM_FILE)) {
    console.log('Downloading Montreal OSM extract...');
    await download(DOWNLOAD_URL, OSM_FILE);
    console.log('✓ Download complete');
  } else {
    console.log('✓ OSM extract already exists');
  }

  console.log('\nStarting GraphHopper container...');
  execSync('docker-compose -f docker-compose.graphhopper.yml up -d', { stdio: 'inherit' });

  console.log('\nGraphHopper container started!');
  console.log('   Container: velosim-graphhopper');
  console.log('   API: http://localhost:8989');
  console.log('\nMonitor logs:');
  console.log('   npm run graphhopper:logs');
}

main().catch((error) => {
  console.error('\nError preparing GraphHopper:', error.message);
  process.exit(1);
});
