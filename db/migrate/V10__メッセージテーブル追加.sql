CREATE TABLE IF NOT EXISTS "メッセージ" (
                                       "message_no" SERIAL NOT NULL,
                                       "from_user_id" VARCHAR(32) NOT NULL,
                                       "to_user_id" VARCHAR(32) NOT NULL,
                                       "anonymous" BOOLEAN NOT NULL,
                                       "message" TEXT NOT NULL,
                                       "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                       PRIMARY KEY ("message_no")
                                   );
