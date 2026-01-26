require('dotenv').config();
const express = require('express');
const cors = require('cors');
const app = express();

// Middleware
app.use(cors({
  origin: process.env.CORS_ORIGIN || '*'
}));
app.use(express.json());

// Routes
const simulationRoutes = require('./routes/simulation');
const dataRoutes = require('./routes/data');

app.use('/api/simulation', simulationRoutes);
app.use('/api/data', dataRoutes);

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Error handler
app.use((err, req, res, next) => {
  console.error('Error:', err);
  res.status(500).json({ 
    error: 'Bir hata oluştu', 
    message: process.env.DEBUG === 'true' ? err.message : undefined 
  });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`🚀 WhatIf TR Backend running on port ${PORT}`);
  console.log(`📊 Environment: ${process.env.DEBUG === 'true' ? 'Development' : 'Production'}`);
});
