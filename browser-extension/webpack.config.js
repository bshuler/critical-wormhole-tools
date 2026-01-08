import path from 'path';
import { fileURLToPath } from 'url';
import CopyPlugin from 'copy-webpack-plugin';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default {
  entry: {
    background: './src/background.js',
    popup: './src/popup/popup.js',
    settings: './src/settings/settings.js'
  },
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: '[name].js',
    clean: true
  },
  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: [
              ['@babel/preset-env', { targets: 'defaults' }]
            ]
          }
        }
      }
    ]
  },
  plugins: [
    new CopyPlugin({
      patterns: [
        { from: 'manifest.json', to: 'manifest.json' },
        { from: 'src/popup/popup.html', to: 'popup.html' },
        { from: 'src/popup/popup.css', to: 'popup.css' },
        { from: 'src/settings/settings.html', to: 'settings.html' },
        { from: 'src/settings/settings.css', to: 'settings.css' },
        { from: 'icons', to: 'icons', noErrorOnMissing: true },
        { from: 'src/content', to: 'content', noErrorOnMissing: true },
        { from: 'src/viewer/viewer.html', to: 'viewer.html' },
        { from: 'src/viewer/viewer.js', to: 'viewer.js' },
        { from: 'src/sandbox/sandbox.html', to: 'sandbox.html' }
      ]
    })
  ],
  resolve: {
    extensions: ['.js'],
    fallback: {
      buffer: 'buffer/'
    }
  },
  optimization: {
    // Don't split chunks for extension - service worker needs all code in one file
    splitChunks: false
  },
  devtool: 'source-map'
};
