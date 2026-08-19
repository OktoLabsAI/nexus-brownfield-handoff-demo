-- CreateTable
CREATE TABLE "RateLimitEvent" (
    "id" SERIAL NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "ip" TEXT NOT NULL,
    "endpoint" TEXT NOT NULL,
    "userId" INTEGER,

    CONSTRAINT "RateLimitEvent_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "RateLimitEvent_ip_createdAt_idx" ON "RateLimitEvent"("ip", "createdAt");

-- CreateIndex
CREATE INDEX "RateLimitEvent_userId_createdAt_idx" ON "RateLimitEvent"("userId", "createdAt");

-- AddForeignKey
ALTER TABLE "RateLimitEvent" ADD CONSTRAINT "RateLimitEvent_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;
