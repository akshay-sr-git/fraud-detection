import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import cookieParser from 'cookie-parser';
import { config } from './config.js';
import healthRouter from './routes/health.js';
import authRouter from './routes/auth.js';
import usersRouter from './routes/users.js';
import { notFound, errorHandler } from './middleware/errorHandler.js';

const app = express();

app.use(helmet());
app.use(cors({ origin: config.corsOrigin, credentials: true }));
app.use(express.json({ limit: '10kb' }));
app.use(cookieParser());
if (config.env !== 'test') {
  app.use(morgan(config.env === 'production' ? 'combined' : 'dev'));
}

app.use('/api/health', healthRouter);
app.use('/api/auth', authRouter);
app.use('/api/users', usersRouter);

app.use(notFound);
app.use(errorHandler);

export default app;