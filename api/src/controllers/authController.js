const { PrismaClient } = require('@prisma/client');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken'); // Changed from jwt-simple to standard jsonwebtoken

const prisma = new PrismaClient();
const JWT_SECRET = process.env.JWT_SECRET || 'secret';

const register = async (req, res) => {
  try {
    const { 
      email, 
      password, 
      role, 
      firstName, 
      lastName, 
      phone, 
      managerFirstName, 
      managerLastName, 
      companyName, 
      companyType 
    } = req.body;
    
    // Validations base
    if (!email || !password) {
      return res.status(400).json({ detail: 'Email and password are required' });
    }

    // Check if user exists
    const existing = await prisma.user.findUnique({ where: { email } });
    if (existing) {
      return res.status(400).json({ detail: 'User already exists with this email' });
    }

    const hashedPassword = await bcrypt.hash(password, 10);
    const assignedRole = role || 'personal';

    // Validation for specialized roles
    if (assignedRole === 'personal' && (!firstName || !lastName || !phone)) {
      return res.status(400).json({ detail: 'Missing personal fields' });
    }
    
    if (assignedRole === 'enterprise' && (!companyName || !companyType || !managerFirstName || !managerLastName)) {
      return res.status(400).json({ detail: 'Missing enterprise fields' });
    }

    const user = await prisma.user.create({
      data: {
        email,
        password: hashedPassword,
        role: assignedRole,
        firstName,
        lastName,
        phone,
        managerFirstName,
        managerLastName,
        companyName,
        companyType
      }
    });

    res.json({ message: 'User created successfully', email: user.email });
  } catch (error) {
    console.error("Register err", error);
    res.status(500).json({ detail: 'Internal server error while creating user' });
  }
};

const login = async (req, res) => {
  try {
    const { email, password } = req.body;
    
    if (!email || !password) {
        return res.status(400).json({ detail: 'Email and password are required' });
    }

    let user = await prisma.user.findUnique({ where: { email } });
    
    if (!user) {
      return res.status(401).json({ detail: 'User not found' });
    }

    const match = await bcrypt.compare(password, user.password);
    if (!match) {
        return res.status(401).json({ detail: 'Invalid credentials' });
    }

    const payload = {
      sub: user.id,
      email: user.email,
      role: user.role,
    };

    // Correct payload for jsonwebtoken
    const token = jwt.sign(payload, JWT_SECRET, { expiresIn: '1h' });

    res.json({
      access_token: token,
      token_type: 'bearer',
      role: user.role
    });
  } catch (error) {
    console.error("Login err: ", error);
    res.status(500).json({ detail: 'Internal Server Error' });
  }
};

module.exports = {
  register,
  login
};
