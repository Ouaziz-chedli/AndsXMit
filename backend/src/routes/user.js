const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/authMiddleware');
const { getMe, updateMe } = require('../controllers/userController');

// All /api/user routes require auth
router.use(authenticate);

router.get('/me', getMe);
router.put('/me', updateMe);

module.exports = router;
