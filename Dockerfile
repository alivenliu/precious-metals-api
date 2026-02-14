# 使用 Node.js 官方镜像
FROM node:18-slim

# 设置工作目录
WORKDIR /app

# 复制 package.json 和 package-lock.json
COPY package*.json ./

# 安装依赖
RUN npm install --production

# 复制项目文件
COPY . .

# 暴露端口 (Railway 会自动注入 PORT 环境变量)
EXPOSE 3000

# 启动应用
CMD ["npm", "start"]
