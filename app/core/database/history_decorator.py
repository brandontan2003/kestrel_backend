import uuid
from sqlalchemy import event

def register_history(history_model):
    """
    Automatically mirror inserts and status updates 
    directly into a history model.
    """

    def decorator(prod_model):
        
        def write_history(connection, target):
            # 1. Dynamically read the primary key column name of the history table
            pk_name = list(history_model.__table__.primary_key.columns.keys())[0]
            
            # 2. Map overlapping database columns between production and history models
            payload = {
                c.key: getattr(target, c.key) 
                for c in prod_model.__table__.columns 
                if hasattr(history_model, c.key)
            }
            
            # 3. Add a fresh runtime uuid for the history log's primary key tracking
            payload[pk_name] = str(uuid.uuid4())
            
            # 4. Insert data directly using connection context to prevent recursion
            connection.execute(history_model.__table__.insert().values(**payload))

        @event.listens_for(prod_model, "after_insert")
        def track_insert(mapper, connection, target):
            write_history(connection, target)

        @event.listens_for(prod_model, "after_update")
        def track_update(mapper, connection, target):
            write_history(connection, target)

        return prod_model
    return decorator
