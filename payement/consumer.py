from main import redis, Order
import time

key = "refund_order"
group = "payement-group"

try:
    redis.xgroup_create(key, group, '$', mkstream=True)
except:
    print('Group already exists!')

while True:
    try:
        results = redis.xreadgroup(group, group, {key: '>'}, None)
        if results != []:
          for result in results:
            msg_id = result[1][0][0]
            obj = result[1][0][1]
            order = Order.get(obj['pk'])
            if order:
              print(order)
              order.status = 'refunded'
              order.save()
            redis.xack(key, group, msg_id)
        
    except Exception as e:
        print(str(e))
    time.sleep(1)
