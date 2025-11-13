import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import pluginImport from 'eslint-plugin-import'
import pluginPrettier from 'eslint-plugin-prettier'

export default defineConfigWithVueTs(
  {
    name: 'app/files-to-lint',
    files: ['**/*.{ts,mts,tsx,vue}'],
  },

  // Global ignores
  {
    ignores: ['**/dist/**', '**/dist-ssr/**', '**/coverage/**', '**/node_modules/**'],
  },

  // Environment and language options
  {
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        console: 'readonly',
        process: 'readonly',
        Buffer: 'readonly',
        __dirname: 'readonly',
        __filename: 'readonly',
        global: 'readonly',
        module: 'readonly',
        require: 'readonly',
        exports: 'readonly',
        window: 'readonly',
        document: 'readonly',
        navigator: 'readonly',
        localStorage: 'readonly',
        sessionStorage: 'readonly',
      },
    },
  },

  // Vue plugin configuration
  ...pluginVue.configs['flat/essential'],

  // TypeScript configuration
  vueTsConfigs.recommended,

  // Prettier configuration
  {
    plugins: {
      prettier: pluginPrettier,
      import: pluginImport,
    },
    rules: {
      // Console rules
      'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',

      // Vue specific rules
      'vue/no-v-model-argument': 'off',
      'vue/no-multiple-template-root': 'off',
      'vue/no-v-for-template-key': 'off',
      'vue/no-v-html': 'off',

      // Disable conflicting Vue formatting rules
      'vue/html-indent': 'off',
      'vue/max-attributes-per-line': 'off',
      'vue/first-attribute-linebreak': 'off',
      'vue/html-closing-bracket-newline': 'off',
      'vue/html-self-closing': 'off',
      'vue/attributes-order': 'off',
      'vue/block-lang': 'off',

      // Import rules - disable problematic ones for now
      'import/no-unresolved': 'off',
      'import/named': 'off',
      'import/default': 'off',
      'import/namespace': 'off',
      'import/no-named-as-default': 'off',
      'import/no-named-as-default-member': 'off',
      'import/no-duplicates': 'off',

      // Prettier rules
      'prettier/prettier': [
        'error',
        {
          endOfLine: 'auto',
          insertFinalNewline: false,
          semi: false,
          singleQuote: true,
          printWidth: 100,
        },
      ],
    },
    settings: {
      'import/resolver': {
        alias: {
          map: [
            ['@', './src'],
            ['@app', './src/app'],
            ['@pages', './src/pages'],
            ['@widgets', './src/widgets'],
            ['@features', './src/features'],
            ['@entities', './src/entities'],
            ['@shared', './src/shared'],
            ['~', './src'],
          ],
          extensions: ['.js', '.ts', '.vue'],
        },
      },
      'import/extensions': ['.js', '.ts', '.vue'],
      'import/parsers': {
        '@typescript-eslint/parser': ['.ts'],
        'vue-eslint-parser': ['.vue'],
      },
    },
  },
)
