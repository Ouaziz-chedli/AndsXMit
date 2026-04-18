const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

const getMe = async (req, res) => {
  try {
    const user = await prisma.user.findUnique({
      where: { id: req.user.sub },
      select: {
        id: true, email: true, role: true,
        firstName: true, lastName: true, phone: true,
        managerFirstName: true, managerLastName: true,
        companyName: true, companyType: true,
        createdAt: true
      }
    });

    if (!user) return res.status(404).json({ detail: 'User not found' });

    // Mock Vector DB info from backend as requested
    res.json({
      user,
      vectorDb: {
        status: 'Active',
        documents: 12
      }
    });
  } catch (error) {
    console.error('getMe err:', error);
    res.status(500).json({ detail: 'Internal server error' });
  }
};

const updateMe = async (req, res) => {
  try {
    const updates = req.body;
    
    // Disallow updating email/role for simplicity here, or extract only allowed fields
    const { email, role, id, password, ...allowedUpdates } = updates;

    const user = await prisma.user.update({
      where: { id: req.user.sub },
      data: allowedUpdates,
      select: {
        id: true, email: true, role: true,
        firstName: true, lastName: true, phone: true,
        managerFirstName: true, managerLastName: true,
        companyName: true, companyType: true,
        createdAt: true
      }
    });

    res.json({ message: 'Profile updated', user });
  } catch (error) {
    console.error('updateMe err:', error);
    res.status(500).json({ detail: 'Internal server error' });
  }
};

module.exports = { getMe, updateMe };
