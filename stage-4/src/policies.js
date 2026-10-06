'use strict';
// Restaurant booking policies (stage 3): managers publish complete, immutable
// policies; versions count up per restaurant and only successful writes
// allocate one.

const { ApiError, notFound } = require('./errors');
const { parsePolicy, publicPolicy } = require('./policy');

function restaurantOr404(store, id) {
  const restaurant = store.restaurants.get(id);
  if (!restaurant) throw notFound('unknown restaurant');
  return restaurant;
}

// The restaurant, if it exists (404) and `user` manages it (403).
function managedRestaurant(store, user, restaurantId) {
  const restaurant = restaurantOr404(store, restaurantId);
  if (!restaurant.manager_user_ids.includes(user.id)) {
    throw new ApiError(403, 'forbidden', 'only a manager of this restaurant may do that');
  }
  return restaurant;
}

function publish(store, user, body, restaurantId) {
  const restaurant = managedRestaurant(store, user, restaurantId);
  const list = store.policiesOf(restaurant.id);
  const policy = { ...parsePolicy(body, restaurant), policy_version: list.length + 1 };
  list.push(policy);
  store.bumpRevision(restaurant.id);
  return { status: 201, body: publicPolicy(policy) };
}

function listPolicies(store, restaurantId) {
  const restaurant = restaurantOr404(store, restaurantId);
  return { status: 200, body: { policies: store.policiesOf(restaurant.id).map(publicPolicy) } };
}

module.exports = { publish, listPolicies, managedRestaurant };
