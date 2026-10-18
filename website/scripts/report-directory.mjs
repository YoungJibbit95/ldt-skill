import { mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';

export async function createReportDirectory(output) {
  const directory = resolve(output);
  await mkdir(dirname(directory), { recursive: true });
  // The series itself must be new: never replace or merge prior evidence.
  await mkdir(directory);
  return directory;
}
