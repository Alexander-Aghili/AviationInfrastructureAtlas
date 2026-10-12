import {defineConfig} from 'vite';
// Relative base so the build works under any path, e.g. /aviation-infrastructure-atlas/.
// web/ is committed: the website publishes it without a build step.
export default defineConfig({base:'./',build:{outDir:'web',emptyOutDir:true}});
