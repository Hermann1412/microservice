# ─────────────────────────────────────────────
# Inventory Consumer  –  run with: python consumer.py
#
# Listens on the Redis Stream "order_completed".
# When the Payment service finishes an order it publishes
# the order data to that stream. This consumer:
#   1. Reads the event
#   2. Finds the matching product
#   3. Decrements its quantity by the ordered amount
#   4. If the product no longer exists, fires a refund event
#      on the "refund_order" stream for the Payment consumer
# ─────────────────────────────────────────────

from main import redis, Product  # reuse the same Redis connection and model
import time

key   = "order_completed"   # stream this consumer reads from
group = "inventory-group"   # consumer-group name (Redis tracks progress per group)

# Create the consumer group once. mkstream=True creates the stream key if it
# doesn't exist yet. '$' means "only new messages from this point forward".
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

                product = Product.get(obj['product_id'])

                if product:
                    print(product)
                    product.quantity = product.quantity - int(obj['quantity'])
                    product.save()
                else:
                    # Product was deleted between order creation and completion.
                    # Send the full order data to the refund stream so the
                    # Payment consumer can mark the order as refunded.
                    redis.xadd('refund_order', obj)

                # Acknowledge the message so it is not redelivered on the next loop
                redis.xack(key, group, msg_id)

    except Exception as e:
        print(str(e))

    time.sleep(1)  # poll every second
