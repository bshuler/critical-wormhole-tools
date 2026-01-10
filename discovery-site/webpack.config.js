import path from 'path';
import { fileURLToPath } from 'url';
import CopyPlugin from 'copy-webpack-plugin';
import HtmlWebpackPlugin from 'html-webpack-plugin';
import MiniCssExtractPlugin from 'mini-css-extract-plugin';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default (env, argv) => {
  const isProduction = argv.mode === 'production';

  return {
    entry: {
      app: './src/app.js',
      viewer: './src/viewer.js'
    },
    output: {
      path: path.resolve(__dirname, 'dist'),
      filename: '[name].[contenthash].js',
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
        },
        {
          test: /\.css$/,
          use: [
            MiniCssExtractPlugin.loader,
            'css-loader'
          ]
        }
      ]
    },
    plugins: [
      new HtmlWebpackPlugin({
        template: './src/index.html',
        filename: 'index.html',
        chunks: ['app']
      }),
      new HtmlWebpackPlugin({
        template: './src/viewer.html',
        filename: 'viewer.html',
        chunks: ['viewer']
      }),
      new MiniCssExtractPlugin({
        filename: 'styles/[name].[contenthash].css'
      }),
      new CopyPlugin({
        patterns: [
          { from: 'src/sandbox.html', to: 'sandbox.html' },
          { from: 'public/icons', to: 'icons', noErrorOnMissing: true },
          { from: 'public/favicon.ico', to: 'favicon.ico', noErrorOnMissing: true }
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
      splitChunks: {
        chunks: 'all',
        cacheGroups: {
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendors',
            chunks: 'all'
          },
          lib: {
            test: /[\\/]src[\\/]lib[\\/]/,
            name: 'wormhole-lib',
            chunks: 'all',
            priority: 10
          }
        }
      }
    },
    devtool: isProduction ? 'source-map' : 'eval-source-map',
    devServer: {
      static: {
        directory: path.join(__dirname, 'dist')
      },
      compress: true,
      port: 3000,
      hot: true,
      historyApiFallback: {
        rewrites: [
          { from: /^\/viewer/, to: '/viewer.html' }
        ]
      }
    }
  };
};
