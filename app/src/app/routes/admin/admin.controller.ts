import { NextFunction, Request, Response, Router } from 'express';
import auth from '../auth/auth';
import prisma from '../../../prisma/prisma-client';

const router = Router();

/**
 * Get admin rate-limit metrics
 * @auth required
 * @route {GET} /api/admin/metrics
 * @returns metrics list of endpoint metrics
 */
router.get(
  '/admin/metrics',
  auth.required,
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const oneMinuteAgo = new Date(Date.now() - 60000);
      const events = await prisma.rateLimitEvent.findMany({
        where: {
          createdAt: {
            gte: oneMinuteAgo,
          },
        },
      });

      const grouped: { [endpoint: string]: { authenticated: number; anonymous: number } } = {};
      for (const event of events) {
        if (!grouped[event.endpoint]) {
          grouped[event.endpoint] = { authenticated: 0, anonymous: 0 };
        }
        if (event.userId !== null) {
          grouped[event.endpoint].authenticated++;
        } else {
          grouped[event.endpoint].anonymous++;
        }
      }

      const metrics = Object.keys(grouped).map((endpoint) => {
        const authCount = grouped[endpoint].authenticated;
        const anonCount = grouped[endpoint].anonymous;
        return {
          endpoint,
          authenticated: {
            count: authCount,
            limit: 100,
            exceeded: authCount > 100,
          },
          anonymous: {
            count: anonCount,
            limit: 20,
            exceeded: anonCount > 20,
          },
        };
      });

      res.json({ metrics });
    } catch (error) {
      next(error);
    }
  },
);

export default router;
