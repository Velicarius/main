#!/usr/bin/env node

/**
 * Защитный скрипт против использования legacy insights API
 * Проверяет что нет импортов insightsV2API или /insights/v2/analyze
 */

const fs = require('fs');
const path = require('path');

const FORBIDDEN_PATTERNS = [
  /insightsV2API/g,
  /insights-v2/g,
  /\/insights\/v2\/analyze/g,
  /api-insights(?!-)/g,  // api-insights без суффикса запрещен
];

const ALLOWED_EXCEPTIONS = [
  'api-insights-optimized',
  'scripts/check-legacy-imports.js'
];

function checkFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const relativePath = path.relative(process.cwd(), filePath);
  
  // Пропускаем исключения
  if (ALLOWED_EXCEPTIONS.some(pattern => relativePath.includes(pattern))) {
    return [];
  }
  
  const violations = [];
  
  FORBIDDEN_PATTERNS.forEach((pattern, index) => {
    const matches = content.match(pattern);
    if (matches) {
      matches.forEach(match => {
        const lineNumber = content.substring(0, content.indexOf(match)).split('\n').length;
        violations.push({
          file: relativePath,
          line: lineNumber,
          pattern: pattern.source,
          match: match
        });
      });
    }
  });
  
  return violations;
}

function scanDirectory(dir) {
  let violations = [];
  
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    
    if (entry.isDirectory()) {
      // Пропускаем node_modules и похожие 
      if (!entry.name.startsWith('.') && !entry.name.includes('node_modules') && !entry.name.includes('dist')) {
        violations = violations.concat(scanDirectory(fullPath));
      }
    } else if (entry.isFile() && (fullPath.endsWith('.ts') || fullPath.endsWith('.tsx') || fullPath.endsWith('.js'))) {
      violations = violations.concat(checkFile(fullPath));
    }
  }
  
  return violations;
}

console.log('🔍 Checking for legacy insights API usage...');

const violations = scanDirectory('frontend/src');

if (violations.length === 0) {
  console.log('✅ No legacy insights API usage found!');
  process.exit(0);
} else {
  console.log('❌ Found legacy insights API usage:');
  violations.forEach(violation => {
    console.log(`   ${violation.file}:${violation.line} - Found "${violation.match}" (pattern: ${violation.pattern})`);
  });
  console.log('\n🚫 Build failed! Remove all legacy API usage and migrate to unified insights API.');
  console.log('📚 See: backend/app/routers/ai_insights_unified.py for new API.');
  process.exit(1);
}


