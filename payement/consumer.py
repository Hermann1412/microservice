# ─────────────────────────────────────────────
# Payment Consumer  –  run with: python consumer.py
#
# Listens on the Redis Stream "refund_order".
# The Inventory consumer publishes to that stream when a
# completed order references a product that no longer exists.
# This consumer then marks the corresponding order as "refunded".
# ─────────────────────────────────────────────

from main import redis, Order  # reuse the same Redis connection and model
import time

key   = "refund_order"    # stream this consumer reads from
group = "payement-group"  # consumer-group name

# Create the consumer group once. mkstream=True creates the stream if needed.
# '$' means only listen for new messages from this point forward.
try:
    redis.xgroup_create(key, group, '$', mkstream=True)
except:
    print('Group already exists!')

# ── Main loop ────────────────────────────────
while True:
    try:
        # xreadgroup: read undelivered messages ('>') for this group.
        # Returns: [[stream_name, [(msg_id, {field: value}), ...]]]
        results = redis.xreadgroup(group, group, {key: '>'}, None)

        if results != []:
            for result in results:
                msg_id = result[1][0][0]   # Redis message ID, needed for xack
                obj    = result[1][0][1]   # the actual field/value dict

                # obj contains the full order dict including its pk
                order = Order.get(obj['pk'])

                if order:
                    print(order)
                    order.status = 'refunded'
                    order.save()

                # Acknowledge the message so it is not redelivered on the next loop
                redis.xack(key, group, msg_id)

    except Exception as e:
        print(str(e))

    time.sleep(1)  # poll every second
