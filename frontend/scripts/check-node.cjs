const major = Number(process.versions.node.split('.')[0]);
if (major !== 24) {
  console.error([
    '',
    `Looksy: нужна Node.js 24 LTS. Сейчас используется ${process.version}.`,
    'Обновите Node.js до 24.x, полностью перезапустите VS Code и проверьте: node --version',
    'Затем выполните из папки frontend: npm.cmd ci и npm.cmd run dev',
    'Инструкция: docs/local-setup.md (в корне репозитория).',
    '',
  ].join('\n'));
  process.exit(1);
}
